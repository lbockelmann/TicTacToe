from socket import *
import select
import threading

####CLIENT VARIABLES####
serverName = raw_input('Name of server(type "localhost"): ')       #Comment These out for testing faster
serverPort = int(raw_input('Server port number(type "10123"): '))        #_________________________________________
#serverName = 'localhost'                                   #Then uncomment these 
#serverPort = 10123                                         #
clientSocket = socket(AF_INET, SOCK_STREAM)
clientSocket.connect((serverName,serverPort))               #Setting up client socket
playerID = ''                                               #This variable represents login name

####HELPER FUNCTIONS####
def printHelp():
    print ''
    print 'login: '
    print '       Make a name for yourself to play the game with. This is required to play the game.'
    print ''
    print 'place: '
    print '       Make a move on the Tic-Tac-Toe board by selecting the space you wish to play.'
    print '       The spaces are numbered 1-9 inclusively. From left to right, 1-3 is the top row,'
    print '       4-6 is the middle row, and 7-9 is the bottom row. Input must be single digit from 1-9.'
    print ''
    print 'games: '
    print '       Display a list of the current ongoing games in the server.' 
    print ''
    print 'who: '
    print '       Display a list of all players logged in and their availability'
    print ''
    print 'play: '
    print '       Choose a player by name that you want to play with. The player must be available.'
    print ''
    print 'automatch: '
    print '       Automatically get matched with another player that is currently available.'
    print ''
    print 'observe: '
    print '       Observe a game that is currently in progress. You cannot observe multiple games at the'
    print '       same time. Also, you cannot observe a game while you are currently playing in a game.'
    print ''
    print 'unobserve: '
    print '       Stop observing a game that you are currently observing.'
    print ''
    print 'comment: '
    print '       Enter a chat message for the current game you are playing in or observing.'
    
    print 'exit: '
    print '       Quit the Tic-Tac-Toe game, and disconnect from the game server.'
    print ''

#This method creates another thread to listen for incoming Server messages, without having to send any data to the server.
#It uses the select method inside. If the socket shuts by the program exiting, it reaches the except and breaks from loop.
def recieveMessage(socket):
    while True:
        try:
            ready = select.select([socket], [], [], 5.0)
            if ready[0]:
                data = socket.recv(1024)
                if data.startswith('\nIt is '):
                    print data
                    print 'Input a command(type "help" for list of commands): '
                elif data.startswith('\n************************************************\n'):   #Accepting incoming win state
                    print data
                    print '\n Game complete \n'
                    print '\nInput a command(type "help" for list of commands): '
                elif data.startswith('\n------------------------------------------------\n'):   #Accepting incoming draw state
                    print data
                    print '\n Game complete \n'
                    print '\nInput a command(type "help" for list of commands): '
                elif data.startswith('\nGame ended due to the exit of '):                       #Accepting incoming exited player message 
                    print data
                    print '\nInput a command(type "help" for list of commands): '
                elif data.startswith('\n(GAME CHAT)'):
                    print data
                    print '\nInput a command(type "help" for list of commands): '
        except:
            break
        
##############################################################################    
print '\n                     Welcome To Tic-Tac-Toe                      '
print '$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$'

listenThread = threading.Thread(target=recieveMessage,args=(clientSocket,)).start()             #Creates the listener thread for incoming server messages.
inputCommand = ''

#This is the command loop. While the user doesn't enter exit, the loop askes for more commands. Only valid commands are excepted
while inputCommand!='exit': 
    inputCommand = raw_input('\nInput a command(type "help" for list of commands): ')
    while((inputCommand!='help')and(inputCommand!='login')and(inputCommand!='place')and(inputCommand!='games')and(inputCommand!='who')and(inputCommand!='play')and(inputCommand!='exit')and(inputCommand!='automatch')and(inputCommand!='observe')and(inputCommand!='unobserve')and(inputCommand!='comment')):
        inputCommand = raw_input('\nInvalid Command, Input valid command(type "help for list of commands): ')

    #Handles help case
    if(inputCommand == 'help'):
        printHelp()
    
    #Handles login case
    elif((inputCommand == 'login')and(playerID != '')):
        print '\nYou have already logged in, exit the game and relaunch the client if you wish to change name.'    
    elif(inputCommand == 'login'):
        loginName = raw_input('Type in your player name: ')
        if((len(loginName)>0)):
            print '\nLogging in as ', loginName
            sendName = loginName + 'login'                  #Used to parse what is needed by server
            clientSocket.send(sendName)
            serverReturn = clientSocket.recv(1024)          #Send, recieve, print data for client
            print '\n' + serverReturn
            if serverReturn == 'Successful Login':
                playerID = loginName
        else:
            print '\nYour login must be at least one character.'
            
    #Handles place case
    elif((inputCommand == 'place')and(playerID == '')):
        print '\nYou must first login in order to play the game'
    elif(inputCommand == 'place'):
        cellSelection = raw_input('Type in the board cell you wish to play: ')
        if ((len(cellSelection)>0) and (len(cellSelection)<2)):
            cellSend = cellSelection + playerID + 'place'                   #Used to parse what is needed by server
            clientSocket.send(cellSend)
            serverReturn = clientSocket.recv(1024)                          #Send, recieve, print data for client
            if serverReturn.startswith('\n************************************************\n'):   #Game Complete(win)
                print serverReturn
                print '\n Game complete \n'
            elif serverReturn.startswith('\n------------------------------------------------\n'):   #Game complete(draw)
                print serverReturn
                print '\n Game complete \n'
            else:
                print '\n' + serverReturn                                         #Game still going
        else:
            print '\nCell choice must be single digit from 1 to 9'

    #Handles the games case
    elif(inputCommand == 'games'):
        clientSocket.send(inputCommand)
        gamesString = clientSocket.recv(1024)                               #Send, recieve, print data for client
        print '\n' + gamesString

    #Handles the who case
    elif(inputCommand == 'who'):
        clientSocket.send(inputCommand)
        namesString = clientSocket.recv(1024)                               #Send, recieve, print data for client
        print '\n' + namesString

    #Handles the automatch case
    elif((inputCommand == 'automatch')and(playerID == '')):
        print '\nYou must login in order to play the game.'
    elif(inputCommand == 'automatch'):
        autoMatchSend = playerID + 'automatch'                              #Used to parse what is needed by server
        clientSocket.send(autoMatchSend)
        serverReturn = clientSocket.recv(1024)                              #Send, recieve, print data for client
        print '\n' + serverReturn

    #Handles the observe case
    elif((inputCommand == 'observe')and(playerID == '')):
        print '\nYou must login in order to observe a game.'
    elif(inputCommand == 'observe'):
        gameID = raw_input('Type in the game ID number of the game you wish to observe: ')
        try:
            int(gameID)
            observeSend = gameID + 'observe' + playerID                     #Used to parse what is needed by server
            clientSocket.send(observeSend)
            serverReturn = clientSocket.recv(1024)                          #Send, recieve, print data for client
            print '\n' + serverReturn
        except:
            print 'The game ID must be an integer.'

    #Handles the unobserve case
    #Since only one game can be observed at a time, the server doesn't need the game ID, it can find the game itself.
    elif((inputCommand == 'unobserve')and(playerID == '')):
        print '\nYou are not observing a game.'
    elif(inputCommand == 'unobserve'):
        unobserveSend = playerID + 'unobserve'                              #Used to parse what is needed by server
        clientSocket.send(unobserveSend)
        serverReturn = clientSocket.recv(1024)                              #Send, recieve, print data for client
        print '\n' + serverReturn

    #Handles the comment case
    elif((inputCommand == 'comment')and(playerID =='')):
        print '\nYou must be logged in to make comments.'
    elif(inputCommand =='comment'):
        comment = raw_input('Enter the comment you want to make in the current game chat: ')
        commentSend = playerID + 'comment' + comment                        #Used to parse what is needed by server
        clientSocket.send(commentSend)
        serverReturn = clientSocket.recv(1024)                              #Send, recieve, print data for client
        print '\n' + serverReturn

    #Handles the play case
    elif((inputCommand == 'play')and(playerID == '')):
        print '\nYou must first login in order to play the game'        
    elif(inputCommand == 'play'):
        targetClient = raw_input('Type in the player that you wish to play: ')
        print '\nAttempting to connect with ' + targetClient
        targetClient = targetClient + playerID + 'playTarget'               #Used to parse what is needed by server
        clientSocket.send(targetClient)
        serverReturn = clientSocket.recv(1024)                              #Send, recieve, print data for client
        print '\n' + serverReturn

    #Handles the exit case    
    elif((inputCommand == 'exit')and(playerID=='')):
        print '\nExiting Game...'
        clientSocket.close()
    elif(inputCommand == 'exit'):
        print '\nExiting Game...'
        exitSend = playerID + 'exit'                                        #Used to parse what is needed by server
        clientSocket.send(exitSend)
        serverReturn = clientSocket.recv(1024)                              #Send, recieve data for client
        #Purposely not printing return, so the print is consistent with both exit conditions
        clientSocket.close()                                                #Close the socket and end the program
        
         
    
    
    
