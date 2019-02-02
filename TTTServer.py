import select
import socket
import sys
import Queue

####HELPER FUNCTIONS AND CLASSES####

#This is the function that handles everything that the client sends to the server. Before the server ever sends anything back
#to the client, the data goes through this function first.
#It 2 parameters. clientInput is the actual string that is sent by the client, and write Address is a new player's address(Only used for login to create new player)
#All of the different condition branches have multiple return possibilities.
#If a string is returned to the client that starts with "ERROR:", it means that the clients request was failed due to the listed condition
#All of the ERROR cases are self explanatory, just read what error is returned
#There are also "FATAL ERROR:" returns, which shouldn't happen. If they do, something is strangely broken and needs to be fixed.
def handleClientInput(clientInput, writeAddress):

    #Handle the login
    #This parses clientInput and creates the new player, adding it to the list.
    #Returns success message if successful. Returns error message if the name is already taken
    if clientInput.endswith('login',0,len(clientInput)):
        newClient = clientInput[:-5]
        for p in playerList:
            if newClient == p.playerID:
                return 'ERROR: That name is already logged into the server, choose another.'
        print 'logging in player: ' + newClient
        newPlayer = Player(newClient, writeAddress)
        playerList.append(newPlayer)
        return 'Successful Login'

    #Handle the exit command
    #Parses the client input and exits the player. If the player is in a game, the other player and all observers are alerted.
    #In that case, the game is removed from the gameList, and all clients involved in the game are alerted and set "available"
    elif clientInput.endswith('exit',0,len(clientInput)):
        exitingName = clientInput[:-4]
        for p in playerList:                        #Find player
            if exitingName == p.playerID:
                if p.state == 'busy':
                    for g in gameList:                      #Find game
                        if((g.player1==p)or(g.player2==p)):
                            for o in g.observerList:
                                o.setState('available')
                            playerList.remove(p)            #remove from player list
                            return '\nGame ended due to the exit of ' + exitingName + '\n!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!'
                        elif p in g.observerList:           #Case where the client is an observer, need to remove from observer list before exit
                            g.observerList.remove(p)
                            playerList.remove(p)
                            return 'Exit success'
                else:
                    playerList.remove(p)
                    return 'Exit success'
        return 'FATAL ERROR: SHOULDN"T EVER HAPPEN'        
            
    #Handle the who command
    #This returns a list of all the players(and their states) currently logged into the server
    elif clientInput == 'who':
        if len(playerList)==0:
            return 'No players currently'
        else:
            namesString = '\n  PLAYER LIST  \n----------------------------------------------\n'
            for p in playerList:
                adderString = p.playerID + '      ' + p.state + '\n'
                namesString = namesString + adderString
            return namesString
    
    #Handle the games command
    #This returns a list of all the games that are currently being played on the server 
    elif clientInput == 'games':
        if len(gameList)==0:
            return 'No games are being played currently'
        else:
            gamesString = '\n  GAME LIST  \n------------------------------------------------\n'
            gamesString = '____GAME_ID____      ____PLAYER_1____      ____PLAYER_2____\n'
            for g in gameList:
                adderString = '       ' + str(g.id) + '                ' + g.player1.playerID + '                ' + g.player2.playerID + '\n'
                gamesString = gamesString + adderString
            return gamesString

    #Handle the play command
    #This parses the clientInput and determines if the command is valid from that client
    #If the command can be completed, a new game is created with both of the players.
    #The client that initiates the game will always be player 1(plays as x's), the other is player 2(plays as o's)
    #Player 1 always acts first
    #After the game is created, it gets added to the gameList and both players are set to state "busy"
    #If a game is successfully started, the new board will be sent to both players
    elif clientInput.endswith('playTarget',0,len(clientInput)):
        endRemoved = clientInput[:-10]
        for p in playerList:
            if endRemoved.endswith(p.playerID, 0, len(endRemoved)):
                requestingClient = p.playerID
                requestingPlayerObject = p
                if p.state == 'busy':
                    return 'ERROR: You are already playing or observing a game.'
                targetClient = endRemoved[:-(len(requestingClient))]
                if requestingClient == targetClient:
                    return 'ERROR: You cannot play a game with yourself' 
        playerChecker = 0                   #This is 0 if target not yet found
        availabilityChecker = 0             #This is 0 if target isn't available
        for p in playerList:
            if targetClient == p.playerID:
                playerChecker = 1
                targetPlayerObject = p      #Determine target object
                if p.state == 'available':
                    availabilityChecker = 1
        if playerChecker == 0:
            return 'ERROR: That player does not exist in the player list.'
        elif((playerChecker == 1)and(availabilityChecker == 0)):
            return 'ERROR: That player is not currently available to play.'
        elif((playerChecker == 1)and(availabilityChecker == 1)):    #Case where a game is created
            incrementGameIdentifier()
            newGame = Game(gameIdentifier,requestingPlayerObject,targetPlayerObject)
            gameList.append(newGame)
            requestingPlayerObject.setState('busy')
            targetPlayerObject.setState('busy')
            return createGameString(newGame)

    #Handle the sutomatch command
    #This does the same thing as the play command, except the client is matched with the first available player on the playerList
    #It parses the client input, searches the list.
    #If a game can be started, the initiating client is player 1(plays x's) and the other client is player 2.
    #Game board is returned if successful, error returned if request cannot be done.
    elif clientInput.endswith('automatch',0,len(clientInput)):
        playerName = clientInput[:-9]
        for p in playerList:
            if (p.playerID == playerName):
                if (p.state == 'busy'):
                    return 'ERROR: You are already playing or observing a game.'
                else:
                    for t in playerList:
                        if((t != p)and(t.state == 'available')):
                            incrementGameIdentifier()
                            newGame = Game(gameIdentifier,p,t)                  #Create new game and add to list
                            gameList.append(newGame)
                            p.setState('busy')
                            t.setState('busy')
                            return createGameString(newGame)
                    return 'ERROR: There are no players available for you to automatch with.'
        return 'FATAL ERROR: THIS SHOULDN"T EVER HAPPEN'
                            
    #Handle the place command
    #First, this parses the clientInput to get the client name and requested cell. Then it determines if the client is in a game
    #It then finds the game and checks to see if the move is legal. If it is, the game's cell value is changed accordingly and the game's turn alternates
    #If the game did not reach an end condition, the updated board is returned.
    #If the game completes, either a draw or win board are returned.
    elif clientInput.endswith('place',0,len(clientInput)):
        endRemoved = clientInput[:-5]
        for p in playerList:
            if endRemoved.endswith(p.playerID, 0, len(endRemoved)):
                clientName = endRemoved[1:]
                cellSelection = endRemoved[:(len(endRemoved)-len(p.playerID))]
                if ((cellSelection < '1') or (cellSelection > '9')):
                    return 'ERROR: Not a valid cell selection(Only 1 through 9 accepted)'
                elif(p.state != 'busy'):
                    return 'ERROR: You must currently be in a game to make a move.'
                for g in gameList:
                    if((p==g.player1)or(p==g.player2)):         #Correct game found
                        if((p==g.player1)and(g.turn==1)or(p==g.player2)and(g.turn==0)):
                            return 'ERROR: It is not your turn to act.'
                        elif(cellSelection == '1'):
                            if(g.c1 != '.'):
                                return 'ERROR: That board cell is already taken.'
                            elif(p==g.player1):
                                g.c1='x'
                                g.turn=1
                            elif(p==g.player2):
                                g.c1='o'
                                g.turn=0
                        elif(cellSelection == '2'):
                            if(g.c2 != '.'):
                                return 'ERROR: That board cell is already taken.'
                            elif(p==g.player1):
                                g.c2='x'
                                g.turn=1
                            elif(p==g.player2):
                                g.c2='o'
                                g.turn=0
                        elif(cellSelection == '3'):
                            if(g.c3 != '.'):
                                return 'ERROR: That board cell is already taken.'
                            elif(p==g.player1):
                                g.c3='x'
                                g.turn=1
                            elif(p==g.player2):
                                g.c3='o'
                                g.turn=0
                        elif(cellSelection == '4'):
                            if(g.c4 != '.'):
                                return 'ERROR: That board cell is already taken.'
                            elif(p==g.player1):
                                g.c4='x'
                                g.turn=1
                            elif(p==g.player2):
                                g.c4='o'
                                g.turn=0
                        elif(cellSelection == '5'):
                            if(g.c5 != '.'):
                                return 'ERROR: That board cell is already taken.'
                            elif(p==g.player1):
                                g.c5='x'
                                g.turn=1
                            elif(p==g.player2):
                                g.c5='o'
                                g.turn=0
                        elif(cellSelection == '6'):
                            if(g.c6 != '.'):
                                return 'ERROR: That board cell is already taken.'
                            elif(p==g.player1):
                                g.c6='x'
                                g.turn=1
                            elif(p==g.player2):
                                g.c6='o'
                                g.turn=0
                        elif(cellSelection == '7'):
                            if(g.c7 != '.'):
                                return 'ERROR: That board cell is already taken.'
                            elif(p==g.player1):
                                g.c7='x'
                                g.turn=1
                            elif(p==g.player2):
                                g.c7='o'
                                g.turn=0
                        elif(cellSelection == '8'):
                            if(g.c8 != '.'):
                                return 'ERROR: That board cell is already taken.'
                            elif(p==g.player1):
                                g.c8='x'
                                g.turn=1
                            elif(p==g.player2):
                                g.c8='o'
                                g.turn=0
                        elif(cellSelection == '9'):
                            if(g.c9 != '.'):
                                return 'ERROR: That board cell is already taken.'
                            elif(p==g.player1):
                                g.c9='x'
                                g.turn=1
                            elif(p==g.player2):
                                g.c9='o'
                                g.turn=0
                        else:
                            return 'FATAL ERROR: SHOULDN"T EVER HAPPEN'
                        
                        #Determine if endgame is reached
                        if((g.c1=='x')and(g.c2=='x')and(g.c3=='x')):        #Horizontal Rows
                            return endGame(g, g.player2)
                        elif((g.c4=='x')and(g.c5=='x')and(g.c6=='x')):
                            return endGame(g, g.player2)
                        elif((g.c7=='x')and(g.c8=='x')and(g.c9=='x')):
                            return endGame(g, g.player2)
                        elif((g.c1=='x')and(g.c4=='x')and(g.c7=='x')):      #Vertical Columns
                            return endGame(g, g.player2)
                        elif((g.c2=='x')and(g.c5=='x')and(g.c8=='x')):
                            return endGame(g, g.player2)
                        elif((g.c3=='x')and(g.c6=='x')and(g.c9=='x')):
                            return endGame(g, g.player2)
                        elif((g.c1=='x')and(g.c5=='x')and(g.c9=='x')):      #Diagonals
                            return endGame(g, g.player2)
                        elif((g.c3=='x')and(g.c5=='x')and(g.c7=='x')):
                            return endGame(g, g.player2)
                        elif((g.c1=='o')and(g.c2=='o')and(g.c3=='o')):      #Horizontal Rows
                            return endGame(g, g.player1)
                        elif((g.c4=='o')and(g.c5=='o')and(g.c6=='o')):
                            return endGame(g, g.player1)
                        elif((g.c7=='o')and(g.c8=='o')and(g.c9=='o')):
                            return endGame(g, g.player1)
                        elif((g.c1=='o')and(g.c4=='o')and(g.c7=='o')):      #Vertical Columns
                            return endGame(g, g.player1)
                        elif((g.c2=='o')and(g.c5=='o')and(g.c8=='o')):
                            return endGame(g, g.player1)
                        elif((g.c3=='o')and(g.c6=='o')and(g.c9=='o')):
                            return endGame(g, g.player1)
                        elif((g.c1=='o')and(g.c5=='o')and(g.c9=='o')):      #Diagonals
                            return endGame(g, g.player1)
                        elif((g.c3=='o')and(g.c5=='o')and(g.c7=='o')):
                            return endGame(g, g.player1)

                        #Determine if a draw occurs
                        elif((g.c1!='.')and(g.c2!='.')and(g.c3!='.')and(g.c4!='.')and(g.c5!='.')and(g.c6!='.')and(g.c7!='.')and(g.c8!='.')and(g.c9!='.')):
                            return endGameDraw(g)
                        #Send normal game state after move
                        else:
                            return createGameString(g)
                #This stops observers from making moves
                return 'ERROR: You must be a player in the game to make a move.'

    #Handle the unobserve command
    #This parses clientInput and finds the game that the client is observing.
    #If the request can be completed, the client is removed from the games observerList and set to state 'available'
    elif(clientInput.endswith('unobserve',0,len(clientInput))):
        clientName = clientInput[:-9]
        for g in gameList:
            if((g.player1.playerID==clientName)or(g.player2.playerID==clientName)):
                return 'ERROR: You cannot unobserve a game you are playing in, finish the game or exit.'
            for o in g.observerList:
                if(o.playerID==clientName):
                    g.observerList.remove(o)
                    o.setState('available')
                    return 'Now you are no longer observing game ' + str(g.id)
        return 'ERROR: You are currently not observing a game.'
        
    #Handle the observe command
    #A client can only observe one game at a time, and cannot observe a game if already playing a game.
    #This parses the needed values out of clientInput and finds the requested game.
    #After finding the correct game, a string is returned indicating to the client that he/she is now observing the game
    #Also, the client is set to busy and added to the games observerList
    elif(clientInput.find('observe')>-1):
        indexer = clientInput.find('observe')
        gameID = clientInput[:indexer]
        indexer = indexer + 8
        playerName = clientInput[indexer-1:]
        gameFound = 0
        for g in gameList:
            if (g.id == int(gameID)):
                gameFound = g.id
                gamePointer = g
        if (gameFound == 0):
            return 'ERROR: The specified game ID number is not currently being used'
        for p in playerList:
            if (playerName==p.playerID):
                if (p.state=='busy'):
                    return 'ERROR: You cannot observe a game if you are currently observing or playing a game.'
                else:
                    gamePointer.observerList.append(p)
                    p.setState('busy')
                    return 'You are now observing game number ' + gameID + '. You will see all future actions in the game.'
        return 'FATAL ERROR: THIS SHOULDN"T EVER HAPPEN'

    #Handle the comment command
    #This parses the clientInput to get the needed values and finds the game that the client is playing or observing.
    #If the comment can be made, a string is returned, which will then be parsed inn the sending section.
    elif(clientInput.find('comment')>-1):
        indexer = clientInput.find('comment')
        clientName = clientInput[:indexer]
        indexer = indexer + 7
        comment = clientInput[indexer:]
        for p in playerList:
            if(p.playerID == clientName):
                if(p.state=='available'):
                    return 'ERROR: You cannot comment if you are not playing or observing a game.'
                for g in gameList:
                    for o in g.observerList:
                        if(o == p):
                            return '\n(GAME CHAT)' + clientName + '(NAME END): ' + comment
        return 'FATAL ERROR: THIS SHOULDN"T EVER HAPPEN'

#This class is used to create Player objects. Every logged in client is a player object.
#playerID is the client login name, playerAddress is the address, state is 'available' or 'busy'
#If client is playing or observing a game, the state is 'busy', otherwise it is 'available'
class Player(object):
    def __init__(self, playerID, playerAddress):
        self.playerID = playerID
        self.playerAddress = playerAddress
        self.state = 'available'
    def setState(self, state):
        self.state = state

#This class is used to create and modify games. It has an id to identify it, and two player objects(player1,player2)
#The observerList is used to broadcast data to both players and observers. Players are in the list by default.
#c1-c9 represent the cells of the board, '.' if empty, 'x' if player 1, and 'o' if player 2
class Game(object):
    def __init__(self, id, player1, player2):
        self.id = id
        self.player1 = player1
        self.player2 = player2
        self.observerList = [player1, player2]
        self.turn = 0    #0 indicates player1's turn, and 1 indicates player2's turn
        self.c1 = '.'
        self.c2 = '.'
        self.c3 = '.'
        self.c4 = '.'
        self.c5 = '.'
        self.c6 = '.'
        self.c7 = '.'
        self.c8 = '.'
        self.c9 = '.'

#This is a function to increment the game IDs so that none are the same number
def incrementGameIdentifier():
    global gameIdentifier
    gameIdentifier = gameIdentifier+1

#This function creates the string to represent the game board to be sent to the clients.
def createGameString(game):
    if game.turn == 0:
        gameString = '\nIt is ' + game.player1.playerID + '\'s turn to act\n'
    else:
        gameString = '\nIt is ' + game.player2.playerID + '\'s turn to act\n'
    gameString = gameString + '-------------------------------------------------\n'

    gameString = gameString + '\n ______\n'
    gameString = gameString + '|'+game.c1+'|'+game.c2+'|'+game.c3+'|\ \n'
    gameString = gameString + '|'+game.c4+'|'+game.c5+'|'+game.c6+'| \ \n'
    gameString = gameString + '|'+game.c7+'|'+game.c8+'|'+game.c9+'|  \ \n'
    gameString = gameString + 'GAME BOARD\n' + '\n'
    
    return gameString
    
  #board will look like this ______
  #                         |.|.|.|\
  #                         |.|.|.| \
  #                         |.|.|.|  \
  #                         GAME BOARD  

#This function creates the string to represent the game board in the completed win state to be sent to the clients.
#The function also sets all of the clients in the games observable list to 'available' since the game is over.
def endGame(game, winnerPlayer):
    endGameString = '\n************************************************\n'
    if winnerPlayer == game.player1:
        endGameString = endGameString + '         ' + game.player1.playerID + '  Wins\n'
        endGameString = endGameString + '************************************************\n'
    else:
        endGameString = endGameString + '         ' + game.player2.playerID + '  Wins\n'
        endGameString = endGameString + '************************************************\n'
    endGameString = endGameString + '\n ______\n'
    endGameString = endGameString + '|'+game.c1+'|'+game.c2+'|'+game.c3+'|\ \n'
    endGameString = endGameString + '|'+game.c4+'|'+game.c5+'|'+game.c6+'| \ \n'
    endGameString = endGameString + '|'+game.c7+'|'+game.c8+'|'+game.c9+'|  \ \n'
    endGameString = endGameString + 'GAME BOARD\n' + '\n'

    for o in game.observerList:
        o.setState('available')
    #gameList.remove(game) happens while sending to client.
    
    return endGameString

#This function creates the string to represent the game board in the completed draw state to be sent to the clients.
#The function also sets all of the clients in the games observable list to 'available' since the game is over.
def endGameDraw(game):
    endGameString = '\n------------------------------------------------\n'        
    endGameString = endGameString + '         ' + game.player1.playerID + ' and ' + game.player2.playerID + ' draw\n'
    endGameString = endGameString + '------------------------------------------------\n'
    endGameString = endGameString + '\n ______\n'
    endGameString = endGameString + '|'+game.c1+'|'+game.c2+'|'+game.c3+'|\ \n'
    endGameString = endGameString + '|'+game.c4+'|'+game.c5+'|'+game.c6+'| \ \n'
    endGameString = endGameString + '|'+game.c7+'|'+game.c8+'|'+game.c9+'|  \ \n'
    endGameString = endGameString + 'GAME BOARD\n' + '\n'

    for o in game.observerList:
        o.setState('available')
    #gameList.remove(game) happens while sending to client.
    
    return endGameString
    
################################################################################################################

playerList = [ ]        #List of all the current players
gameList = [ ]          #List of all the current games
gameIdentifier = 0      #This is used to put an ID on each game. Gets incremented with each game

# Create a TCP/IP socket and set blocking
server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server.setblocking(0)

# Bind the socket to the port. Using localhost and port number 10123
server_address = ('localhost', 10123)
print >>sys.stderr, 'starting up on %s port %s' % server_address
server.bind(server_address)

# Listen for incoming connections
server.listen(5)

# Sockets being read from
inputs = [ server ]

# Sockets to we will write to
outputs = [ ]

# Outgoing message queues
message_queues = {}

####THIS IS THE READING AND SENDING SECTION
#### THE MAJOR LOOP FOR THE SERVER TO HANDLE INCOMING AND OUTGOING DATA USING SELECT()################
while inputs:

    # Wait for at least one of the sockets to be ready for processing
    print >>sys.stderr, '\nwaiting for the next event'
    readable, writable, exceptional = select.select(inputs, outputs, inputs)
    # Handle inputs
    for s in readable:

        if s is server:
            # A "readable" server socket is ready to accept a connection
            connection, client_address = s.accept()
            print >>sys.stderr, 'new connection from', client_address
            connection.setblocking(0)
            inputs.append(connection)

            # Give the connection a queue for data we want to send
            message_queues[connection] = Queue.Queue()
        else:
            data = s.recv(1024)
            if data:
                # A readable client socket has data
                print >>sys.stderr, 'received "%s" from %s' % (data, s.getpeername())
                message_queues[s].put(data)
                # Add output channel for response
                if s not in outputs:
                    outputs.append(s)
            else:
                # Interpret empty result as closed connection
                print >>sys.stderr, 'closing', client_address, 'after reading no data'
                # Stop listening for input on the connection
                if s in outputs:
                    outputs.remove(s)
                inputs.remove(s)
                s.close()

                # Remove message queue
                del message_queues[s]
    # Handle outputs
    for s in writable:
        try:
            next_msg = message_queues[s].get_nowait()
        except Queue.Empty:
            # No messages waiting so stop checking for writability.
            print >>sys.stderr, 'output queue for', s.getpeername(), 'is empty'
            outputs.remove(s)
        except KeyError, e:                 #This occurs when a client exits the program, need to except the error to avoid crash
            print 'Player has left'
        else:
            #SENDING SECTION
            next_msg = handleClientInput(next_msg, s)       #Pass input from client into the handleClientInput function along with client address.
            #The following conditional branches send data to multiple clients, without requiring any request for the data.
            #These include game starts, game updates, exit updates, comments
            #Each is parsed based on the start of the return string coming from handleClientInput function.
            if next_msg.startswith('\nIt is '):             #This means that a game state is being sent
                nameFinder = next_msg[7:]
                indexFinder = nameFinder.find('\'s turn to act\n',0,len(nameFinder))
                firstName = nameFinder[:indexFinder]
                errorCheck = 0
                for g in gameList:
                    for o in g.observerList:
                        if o.playerID == firstName:         #Correct game found
                            errorCheck = 1
                            for o in g.observerList:
                                print >>sys.stderr, 'sending "%s" to %s' % (next_msg, o.playerAddress.getpeername())
                                o.playerAddress.send(next_msg)              #Send data to all players observing or playing the game
                if errorCheck == 0:
                    print 'ERROR: SENDING GAME STATE ISSUE'

            elif next_msg.startswith('\n(GAME CHAT)'):             #This means that a comment is being sent
                firstName = next_msg[12:next_msg.find('(NAME END): ',0,len(next_msg))]
                stringParser = next_msg[:12+len(firstName)]
                stringParser = stringParser + next_msg[len(stringParser)+10:]
                next_msg = stringParser
                errorCheck = 0
                for g in gameList:
                    for o in g.observerList:
                        if o.playerID == firstName:         #Correct game found
                            errorCheck = 1
                            for o in g.observerList:
                                print >>sys.stderr, 'sending "%s" to %s' % (next_msg, o.playerAddress.getpeername())
                                o.playerAddress.send(next_msg)              #Send data to all players observing or playing the game
                if errorCheck == 0:
                    print 'ERROR: SENDING GAME STATE ISSUE'        
            elif next_msg.startswith('\n************************************************\n'):   #This means that a game has finished in win
                nameFinder = next_msg[59:]
                indexFinder = nameFinder.find('  Wins\n',0,len(nameFinder))
                firstName = nameFinder[:indexFinder]
                errorCheck = 0
                for g in gameList:
                    for o in g.observerList:
                        if o.playerID == firstName:         #Correct game found
                            errorCheck = 1
                            for o in g.observerList:
                                print >>sys.stderr, 'sending "%s" to %s' % (next_msg, o.playerAddress.getpeername())
                                o.playerAddress.send(next_msg)                  #Send data to all players observing or playing the game
                            gameList.remove(g)
                if errorCheck == 0:
                    print 'ERROR: SENDING GAME STATE ISSUE'
            elif next_msg.startswith('\n------------------------------------------------\n'):   #This means that a game has finished in draw
                nameFinder = next_msg[59:]
                indexFinder = nameFinder.find(' and',0,len(nameFinder))
                firstName = nameFinder[:indexFinder]
                errorCheck = 0
                for g in gameList:
                    for o in g.observerList:
                        if o.playerID == firstName:         #Correct game found
                            errorCheck = 1
                            for o in g.observerList:
                                print >>sys.stderr, 'sending "%s" to %s' % (next_msg, o.playerAddress.getpeername())
                                o.playerAddress.send(next_msg)                  #Send data to all players observing or playing the game
                            gameList.remove(g)
                if errorCheck == 0:
                    print 'ERROR: SENDING GAME STATE ISSUE'
            elif next_msg.startswith('\nGame ended due to the exit of '):   #This means that a player exited without finishing game
                firstName = next_msg[31:-54]
                errorCheck = 0
                for g in gameList:
                    for o in g.observerList:
                        if o.playerID == firstName:         #Correct game found
                            errorCheck = 1
                            for o in g.observerList:
                                print >>sys.stderr, 'sending "%s" to %s' % (next_msg, o.playerAddress.getpeername())
                                o.playerAddress.send(next_msg)              #Send data to all players observing or playing the game
                            gameList.remove(g)
                if errorCheck == 0:
                    print 'ERROR: SENDING GAME STATE ISSUE'
            else:
                #This means that the server message being sent is in response to a request(Not a game state update or comment)
                #In this case, the string being sent to the client is only for that client and not all observers of a game.
                print >>sys.stderr, 'sending "%s" to %s' % (next_msg, s.getpeername())
                s.send(next_msg)                            #Send response message back to client
    # Handle "exceptional conditions"
    for s in exceptional:
        print >>sys.stderr, 'handling exceptional condition for', s.getpeername()
        # Stop listening for input on the connection
        inputs.remove(s)
        if s in outputs:
            outputs.remove(s)
        s.close()

        # Remove message queue
        del message_queues[s]
