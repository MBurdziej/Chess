from PyQt5.QtWidgets import QApplication, QGraphicsScene, QGraphicsView, QVBoxLayout, QHBoxLayout, QWidget, QPushButton, QLineEdit, QMainWindow, QGraphicsPixmapItem, QPlainTextEdit, QLabel, QDialog, QVBoxLayout, QLabel, QComboBox
from PyQt5.QtGui import QPixmap, QBrush
from PyQt5.QtCore import Qt, QTimer, QPointF, QPoint, QObject, pyqtSignal, QThread, pyqtSignal
from PyQt5.QtTest import QTest
import sqlite3
import xml.etree.ElementTree as ET
from datetime import datetime
import json
import socket
import sys
import random

SCALE = 100

class ChessGame(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Chess Game")
        self.central_widget = QWidget()  # Central widget to hold everything
        self.setCentralWidget(self.central_widget)
        self.layout = QHBoxLayout()  # Main layout for the central widget
        self.central_widget.setLayout(self.layout)
        self.logger = ""
        self.move_counter = 0  # Move counter for the game
        self.plus2 = False
        self.submitted_text = ""
        self.chess_board = ChessBoard()
        self.game_mode = "Offline"  # Variable to track current game mode
        self.server_mode = False
        self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.moves = ""
        self.mate_end = False

        # Create chess view and add it to the layout
        self.chess_view = ChessView()
        self.layout.addWidget(self.chess_view)

        #logger
        self.text_field = QPlainTextEdit()
        self.text_field.setPlainText(self.logger)
        self.layout.addWidget(self.text_field)
        self.text_field.setFixedWidth(200)

        # Text input field and button
        self.text_input = QLineEdit()
        self.layout.addWidget(self.text_input)
        self.submit_button = QPushButton("Submit")
        self.submit_button.clicked.connect(self.handle_submit)
        self.layout.addWidget(self.submit_button)

        # Create buttons for timer modes
        self.button_3min = QPushButton("3 min")
        self.button_5min = QPushButton("5 min")
        self.button_10min = QPushButton("10 min")

        # Connect buttons to slots
        self.button_3min.clicked.connect(lambda: self.setupTimer(3 * 60 * 1000))
        self.button_5min.clicked.connect(lambda: self.setupTimer(5 * 60 * 1000))
        self.button_10min.clicked.connect(lambda: self.setupTimer(10 * 60 * 1000))

        # Add buttons to layout
        self.layout.addWidget(self.button_3min)
        self.layout.addWidget(self.button_5min)
        self.layout.addWidget(self.button_10min)

        # Add labels for timers
        self.white_timer_label = QLabel("03:00:0")
        self.black_timer_label = QLabel("03:00:0")
        self.white_timer_label.setGeometry(100, 100, 100, 30)  # Przykładowe współrzędne i rozmiar
        self.black_timer_label.setGeometry(200, 200, 100, 30) 
        self.layout.addWidget(self.white_timer_label)
        self.layout.addWidget(self.black_timer_label)

        # Initialize timers
        self.white_timer = QTimer()
        self.black_timer = QTimer()
        self.white_time = 3 * 60 * 1000
        self.black_time = 3 * 60 * 1000
        self.white_timer.timeout.connect(self.updateWhiteTimer)
        self.black_timer.timeout.connect(self.updateBlackTimer)

        # Create combo box for selecting mode
        self.mode_combo_box = QComboBox()
        self.mode_combo_box.addItem("Offline")
        self.mode_combo_box.addItem("Online")
        self.mode_combo_box.addItem("AI")
        self.mode_combo_box.addItem("AI2")
        self.mode_combo_box.currentIndexChanged.connect(self.toggleMode)
        self.layout.addWidget(self.mode_combo_box)

        # Create buttons
        self.start_button = QPushButton("Start")
        self.stop_button = QPushButton("Stop")
        self.send_game_button = QPushButton("Send game")

        # Connect buttons to slots
        self.start_button.clicked.connect(self.startTimers)
        self.stop_button.clicked.connect(self.stopTimers)
        self.send_game_button.clicked.connect(self.send_game)

        # Add buttons to layout
        self.layout.addWidget(self.start_button)
        self.layout.addWidget(self.stop_button)
        self.layout.addWidget(self.send_game_button)

        self.start_button.setEnabled(True)
        self.stop_button.setEnabled(False)

        # Łączenie z bazą danych
        self.conn = sqlite3.connect('chess_history.db')
        self.cursor = self.conn.cursor()

        # Tworzenie tabeli, jeśli nie istnieje
        self.create_table()

    def toggleMode(self, index):
        if index == 1:  # Online mode selected
            self.toggleOnlineMode()
        elif index == 2:
            self.game_mode = "AI"
        elif index == 3:
            self.game_mode = "AI2"
        else:  # Offline mode selected
            self.game_mode = "Offline"
            self.receive_thread.exit()
            self.client_socket.close()

    def startTimers(self):
        self.white_timer.start(10)
        self.black_timer.start(10)
        self.start_button.setEnabled(False)
        self.stop_button.setEnabled(True)

    def stopTimers(self):
        self.white_timer.stop()
        self.black_timer.stop()
        self.start_button.setEnabled(True)
        self.stop_button.setEnabled(False)

    def setupTimer(self, duration):
        self.white_time = duration
        self.black_time = duration
        self.updateTimerLabel(self.white_timer_label, self.white_time)
        self.updateTimerLabel(self.black_timer_label, self.black_time)
        self.white_timer.stop()
        self.black_timer.stop()
        self.chess_view.remove_all()
        self.chess_view.current_piece = None
        self.chess_view.white_short_castling_possibility = True
        self.chess_view.white_long_castling_possibility = True
        self.chess_view.black_short_castling_possibility = True
        self.chess_view.black_long_castling_possibility = True
        self.chess_view.addChessPieces()
        self.start_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        self.move_counter = 0
        self.logger += "\nRESET"
        self.moves = ""
        self.text_field.setPlainText(self.logger)

    def updateWhiteTimer(self):
        if self.move_counter % 2 == 0:  # Check if it's white player's turn
            self.white_time -= 10  # Decrement time by 10 milliseconds
            self.updateTimerLabel(self.white_timer_label, self.white_time)
    
    def updateBlackTimer(self):
        if self.move_counter % 2 == 1:  # Check if it's black player's turn
            self.black_time -= 10  # Decrement time by 10 milliseconds
            self.updateTimerLabel(self.black_timer_label, self.black_time)

    def updateTimerLabel(self, label, time):
        minutes = int(time / 60000)
        seconds = int((time % 60000) / 1000)
        milliseconds = int((time % 1000) / 10)
        label.setText(f"{minutes:02}:{seconds:02}:{(milliseconds//10):01}")

    def handle_submit(self):
        self.submitted_text = self.text_input.text()
        self.logger += f"\nsubmitted_text: {self.submitted_text}"
        self.text_field.setPlainText(game.logger)
        self.text_input.clear()
        text = self.submitted_text
        letters = ['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h']
        numbers = ['8', '7', '6', '5', '4', '3', '2', '1']
        if len(text) >= 5 and text[0] in letters and text[3] in letters and text[1] in numbers and text[4] in numbers:
            x1, y1, x2, y2 = self.decode(self.submitted_text)
            self.move_by_text(self.submitted_text)
        else:
            self.send_message(self.submitted_text)

    def decode(self, text):
        letters = ['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h']
        numbers = ['8', '7', '6', '5', '4', '3', '2', '1']
        if len(text) >= 5 and text[0] in letters and text[3] in letters and text[1] in numbers and text[4] in numbers:
            x1 = letters.index(text[0])
            y1 = numbers.index(text[1])
            x2 = letters.index(text[3])
            y2 = numbers.index(text[4])
        else:
            return 0, 0, 0, 0

        return x1, y1, x2, y2
    
    def move_by_text(self, text):
        mate = False
        move = ""
        promotion_flag = False
        x1, y1, x2, y2 = self.decode(text)
        item = self.chess_view.itemAt(QPoint(self.chess_view.x() + x1 * SCALE + SCALE//2 , self.chess_view.y() + y1 * SCALE + SCALE//2))
        if(isinstance(item, ChessPiece)):
            targetPos = (x2 * SCALE, y2 * SCALE)
            if (targetPos in item.get_possible_moves()) and ((game.move_counter % 2 == 0 and item.color == 'white') or (game.move_counter % 2 == 1 and item.color == 'black')): # możliwość ruchu dla odpowiedniego gracza
                item.setPos(-100, -100) # przeniesienie figury aby nie wykryło samej siebie przy warunku bicia
                target_item = item.scene().itemAt(targetPos[0] + SCALE//2, targetPos[1] + SCALE//2, QGraphicsView().transform())
                target_item_copy = target_item #kopia do ewentualnego cofnięcia niedozwolonego ruchu w przypadku

                item.setPos(targetPos[0], targetPos[1])
                if isinstance(target_item, ChessPiece): # warunek usunięcia figury przy biciu
                    item.scene().removeItem(target_item)
                elif isinstance(item, Pawn) and targetPos[0] != int(x1 *SCALE):
                    target_item = item.scene().itemAt(game.chess_view.pawn_that_double_jumped_pos[0] + SCALE//2, game.chess_view.pawn_that_double_jumped_pos[1] + SCALE//2, QGraphicsView().transform())
                    target_item_copy = target_item
                    if isinstance(target_item, ChessPiece): # warunek usunięcia figury przy en passant
                        item.scene().removeItem(target_item)

                game.chess_view.updateAttackedSquares()
                

                white_king_pos = (game.chess_view.pieces['white_king'].x(), game.chess_view.pieces['white_king'].y())
                black_king_pos = (game.chess_view.pieces['black_king'].x(), game.chess_view.pieces['black_king'].y())
                #warunki ruchu królem na bite pole
                if not ((game.move_counter % 2 == 0 and white_king_pos in game.chess_view.black_attacked_squares) or (game.move_counter % 2 == 1 and black_king_pos in game.chess_view.white_attacked_squares)):
                    
                    if game.chess_view.white_long_castling_possibility and game.chess_view.findPieceName(item) == 'white_king' and targetPos == (2 * SCALE, 7 * SCALE):
                        game.chess_view.pieces['white_rook_left'].setPos(3 * SCALE, 7 * SCALE)
                    elif game.chess_view.white_short_castling_possibility and game.chess_view.findPieceName(item) == 'white_king' and targetPos == (6 * SCALE, 7 * SCALE):
                        game.chess_view.pieces['white_rook_right'].setPos(5 * SCALE, 7 * SCALE)
                    elif game.chess_view.black_long_castling_possibility and game.chess_view.findPieceName(item) == 'black_king' and targetPos == (2 * SCALE, 0):
                        game.chess_view.pieces['black_rook_left'].setPos(3 * SCALE, 0)
                    elif game.chess_view.black_short_castling_possibility and game.chess_view.findPieceName(item) == 'black_king' and targetPos == (6 * SCALE, 0):
                        game.chess_view.pieces['black_rook_right'].setPos(5 * SCALE, 0)

                    letters = ['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h']
                    numbers = [8, 7, 6, 5, 4, 3, 2, 1]
                    move = f"{letters[x1]}{numbers[y1]}-{letters[x2]}{numbers[y2]}"

                    game.logger = game.logger + f"\n{move}"
                    game.moves = game.moves + f"\n{move}"
                    if game.game_mode == "Online":
                        game.send_message(f"{move}")

                    header = "Chessgame " + "1"
                    moves = f"\n{move}"
                    # game.save_game_history(header, moves)
                    # game.save_game_history_to_xml(header, moves)


                    if isinstance(item, Pawn) and item.y() in [0, 7 * SCALE]:
                        promotion_piece_type = item.promotion()
                        game.chess_view.addPiece(promotion_piece_type, targetPos) #promocja piona
                        promotion_flag = True
                        move = f"promotion-{promotion_piece_type}"

                        game.logger = game.logger + f"\n{move}"
                        game.moves = game.moves + f"\n{move}"
                        if game.game_mode == "Online":
                            game.send_message(f"{move}")

                        header = "Chessgame " + "1"
                        moves = f"\n{move}"
                        # game.save_game_history(header, moves)
                        # game.save_game_history_to_xml(header, moves)



                    moved_piece = game.chess_view.findPieceName(item) #znajdowanie nazwy figury
                    removed_piece = game.chess_view.findPieceName(target_item_copy)
                    item.castling_possibility(moved_piece, removed_piece) #aktualizacja warunków roszady
                    
                    if isinstance(item, Pawn) and abs(targetPos[1] - y1 * SCALE) == 2 * SCALE: #sprawdzenie czy pion przeskoczył o 2 pola
                        game.chess_view.pawn_that_double_jumped_pos = targetPos
                    else:
                        game.chess_view.pawn_that_double_jumped_pos = None

                    # warunki szacha - mata
                    if(white_king_pos in game.chess_view.black_attacked_squares or black_king_pos in game.chess_view.white_attacked_squares):
                        mate = item.mate()
                        #sprawdzenie mata
                        if mate:
                            game.stopTimers()
                            if game.move_counter % 2 == 0:
                                game.logger = game.logger + f"\nMate - White wins"
                            else:
                                game.logger = game.logger + f"\nMate - Black wins"
                            game.mate_end = True
                        else:
                            game.logger = game.logger + f"\nCheck"
                    elif item.mate():
                        game.stopTimers()
                        game.logger = game.logger + f"\nPat"
                        game.mate_end = True

                    game.move_counter += 1
                    game.text_field.setPlainText(game.logger)
                    if not game.mate_end:
                        game.startTimers()
                    # game.chess_view.pieces['white_rook_left'].setPos(3 * SCALE, 7 * SCALE)

                    if promotion_flag:
                        item.scene().removeItem(item)
                    
                    return True

                else: #kiedy król staje na atakowanym polu
                    item.setPos(x1 * SCALE, y1 * SCALE) 
                    game.chess_view.updateAttackedSquares()
                    item.scene().addItem(target_item_copy)
                    return False
            else:
                # Move back to original position if released position is invalid
                item.setPos(x1 * SCALE, y1 * SCALE)
                return False
        
    def create_table(self):
        self.cursor.execute('''CREATE TABLE IF NOT EXISTS games (
                            id INTEGER PRIMARY KEY,
                            timestamp DATETIME,
                            header TEXT,
                            moves TEXT
                            )''')
        self.conn.commit()

    def save_game_history(self, header, moves):
        timestamp = datetime.now()
        self.cursor.execute("INSERT INTO games (timestamp, header, moves) VALUES (?, ?, ?)",
                            (timestamp, header, moves))
        self.conn.commit()

    def save_game_history_to_xml(self, header, moves):
        # Sprawdzenie czy plik XML istnieje
        filename = "chess_history.xml"
        try:
            tree = ET.parse(filename)
            root = tree.getroot()
        except FileNotFoundError:
            # Jeśli plik nie istnieje, utwórz nowe drzewo XML
            root = ET.Element("games")

        # Sprawdzenie czy istnieje gra o podanym nagłówku
        game_exists = False
        for game_element in root.findall("game"):
            if game_element.find("header").text == header:
                moves_element = ET.SubElement(game_element, "moves")
                moves_element.text = moves
                game_exists = True
                break

        if not game_exists:
            # Tworzenie elementu gry
            game_element = ET.SubElement(root, "game")

            # Dodawanie atrybutu timestamp
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            game_element.set("timestamp", timestamp)

            # Dodawanie elementów nagłówka i ruchów
            header_element = ET.SubElement(game_element, "header")
            header_element.text = header

            moves_element = ET.SubElement(game_element, "moves")
            moves_element.text = moves

        # Tworzenie drzewa XML
        tree = ET.ElementTree(root)

        # Zapis drzewa do pliku
        tree.write(filename)

    def toggleOnlineMode(self):
        if self.game_mode != "Online":
            self.game_mode = "Online"
            # Enter online mode setup
            dialog = OnlineDialog()
            if dialog.exec_():
                ip = dialog.ip_input.text()
                port = dialog.port_input.text()
                print(ip, port)
                data = {
                    "game_mode": self.game_mode,
                    "address": ip,
                    "port": port
                }
                with open("online_settings.json", "w") as json_file:
                    json.dump(data, json_file)

            self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.client_socket.connect((ip, int(port)))

            self.receive_thread = ReceiveThread(self.client_socket)
            self.receive_thread.message_received.connect(self.handle_received_message)
            self.receive_thread.start()  # Rozpoczęcie wątku odbierającego wiadomości

    def handle_received_message(self, message):
        game.logger = game.logger + f"\nReceived: {message}"
        game.text_field.setPlainText(game.logger)
        if message[0] == 'G' and message[1] == 'A' and message[2] == 'M' and message[3] =='E':
            self.moves = message.replace("GAME", "")
            self.read_game()
        else:
            self.move_by_text(message)

    def send_message(self, message):
        try:
            self.client_socket.sendall(message.encode())
        except Exception as e:
            print("Error sending message:", e)

    def read_game(self):
        self.chess_view.remove_all()
        self.chess_view.current_piece = None
        self.chess_view.white_short_castling_possibility = True
        self.chess_view.white_long_castling_possibility = True
        self.chess_view.black_short_castling_possibility = True
        self.chess_view.black_long_castling_possibility = True
        self.chess_view.addChessPieces()
        self.start_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        self.move_counter = 0
        self.logger += "\nRESET"
        self.text_field.setPlainText(self.logger)

        self.moves.splitlines()

        moves_2 = self.moves.split("\n")
        for move in moves_2:
            self.move_by_text(move)

        self.moves = ""

    def send_game(self):
        self.send_message(f"GAME{self.moves}")

class OnlineDialog(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Online Mode")
        self.layout = QVBoxLayout()

        self.ip_label = QLabel("IP Address:")
        self.ip_input = QLineEdit()
        self.port_label = QLabel("Port:")
        self.port_input = QLineEdit()

        self.layout.addWidget(self.ip_label)
        self.layout.addWidget(self.ip_input)
        self.layout.addWidget(self.port_label)
        self.layout.addWidget(self.port_input)

        # Combo Box for selecting client/server
        self.mode_label = QLabel("Mode:")
        self.mode_combo_box = QComboBox()
        self.mode_combo_box.addItem("Client")
        self.mode_combo_box.addItem("Server")

        self.layout.addWidget(self.mode_label)
        self.layout.addWidget(self.mode_combo_box)

        # Button for loading from JSON
        self.load_json_button = QPushButton("Load from JSON")
        self.load_json_button.clicked.connect(self.load_from_json)
        self.layout.addWidget(self.load_json_button)

        # OK Button
        self.buttons_layout = QHBoxLayout()
        self.ok_button = QPushButton("OK")
        self.ok_button.clicked.connect(self.accept)

        self.buttons_layout.addWidget(self.ok_button)

        self.layout.addLayout(self.buttons_layout)
        self.setLayout(self.layout)

    def load_from_json(self):
        try:
            with open('online_settings.json', 'r') as file:
                data = json.load(file)
                if 'address' in data and 'port' in data:
                    self.ip_input.setText(data['address'])
                    self.port_input.setText(str(data['port']))
        except FileNotFoundError:
            print("File not found")  # Handle file not found error
        except json.JSONDecodeError:
            print("Error decoding JSON")  # Handle JSON decoding error

class Promotion(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Promotion")
        self.layout = QVBoxLayout()

        self.mode_label = QLabel("Choose piece:")
        self.mode_combo_box = QComboBox()
        self.mode_combo_box.addItem("Queen")
        self.mode_combo_box.addItem("Rook")
        self.mode_combo_box.addItem("Knight")
        self.mode_combo_box.addItem("Bishop")


        self.layout.addWidget(self.mode_label)
        self.layout.addWidget(self.mode_combo_box)

        # OK Button
        self.buttons_layout = QHBoxLayout()
        self.ok_button = QPushButton("OK")
        self.ok_button.clicked.connect(self.accept)

        self.buttons_layout.addWidget(self.ok_button)

        self.layout.addLayout(self.buttons_layout)
        self.setLayout(self.layout)

class ReceiveThread(QThread):
    message_received = pyqtSignal(str)

    def __init__(self, client_socket):
        super().__init__()
        self.client_socket = client_socket

    def run(self):
        while True:
            try:
                data = self.client_socket.recv(1024)
                if not data:
                    print("Disconnected from server.")
                    self.client_socket.close()
                    break
                message = data.decode()
                self.message_received.emit(message)  # Emituj sygnał z otrzymaną wiadomością
            except Exception as e:
                print("Error receiving message:", e)
                break

class ChessView(QGraphicsView):
    def __init__(self):
        super().__init__()
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scene = ChessBoard()
        self.setScene(self.scene)
        self.setFixedHeight(8 * SCALE)
        self.setFixedWidth(8 * SCALE)
        self.pieces = {}
        self.loadChessPieces()
        self.addChessPieces()
        self.current_piece = None
        self.white_short_castling_possibility = True
        self.white_long_castling_possibility = True
        self.black_short_castling_possibility = True
        self.black_long_castling_possibility = True
        self.d1_attacked = False
        self.f1_attacked = False
        self.d8_attacked = False
        self.f8_attacked = False
        self.pawn_that_double_jumped_pos = None
        self.white_attacked_squares = []  # Lista współrzędnych pól atakowanych
        self.black_attacked_squares = []


    def loadChessPieces(self):
        # White pieces
        self.pieces['white_king'] = King('white', 0 , 0)
        self.pieces['white_queen'] = Queen('white', 0, 0)
        self.pieces['white_rook_left'] = Rook('white', 0, 0)
        self.pieces['white_rook_right'] = Rook('white', 0, 0)
        self.pieces['white_bishop_left'] = Bishop('white', 0, 0)
        self.pieces['white_bishop_right'] = Bishop('white', 0, 0)
        self.pieces['white_knight_left'] = Knight('white', 0, 0)
        self.pieces['white_knight_right'] = Knight('white', 0, 0)
        for i in range(8):
            self.pieces[f'white_pawn_{i+1}'] = Pawn('white', 0, 0)

        # Black pieces
        self.pieces['black_king'] = King('black', 0, 0)
        self.pieces['black_queen'] = Queen('black', 0, 0)
        self.pieces['black_rook_left'] = Rook('black', 0, 0)
        self.pieces['black_rook_right'] = Rook('black', 0, 0)
        self.pieces['black_bishop_left'] = Bishop('black', 0, 0)
        self.pieces['black_bishop_right'] = Bishop('black', 0, 0)
        self.pieces['black_knight_left'] = Knight('black', 0, 0)
        self.pieces['black_knight_right'] = Knight('black', 0, 0)
        for i in range(8):
            self.pieces[f'black_pawn_{i+1}'] = Pawn('black', 0, 0)

    def addChessPieces(self):
        for piece in self.pieces.values():
            self.scene.addChessPiece(piece, piece.x(), piece.y())

        for i in range(8):
            self.pieces[f'white_pawn_{i+1}'].setPos(i * SCALE, 6 * SCALE)
            self.pieces[f'black_pawn_{i+1}'].setPos(i * SCALE, 1 * SCALE)
        self.pieces[f'white_king'].setPos(4 * SCALE, 7 * SCALE)
        self.pieces[f'white_queen'].setPos(3 * SCALE, 7 * SCALE)
        self.pieces[f'white_rook_left'].setPos(0, 7 * SCALE)
        self.pieces[f'white_rook_right'].setPos(7 * SCALE, 7 * SCALE)
        self.pieces[f'white_bishop_left'].setPos(2 * SCALE, 7 * SCALE)
        self.pieces[f'white_bishop_right'].setPos(5 * SCALE, 7 * SCALE)
        self.pieces[f'white_knight_left'].setPos(1 * SCALE, 7 * SCALE)
        self.pieces[f'white_knight_right'].setPos(6 * SCALE, 7 * SCALE)
        self.pieces[f'black_king'].setPos(4 * SCALE, 0)
        self.pieces[f'black_queen'].setPos(3 * SCALE, 0)
        self.pieces[f'black_rook_left'].setPos(0, 0)
        self.pieces[f'black_rook_right'].setPos(7 * SCALE, 0)
        self.pieces[f'black_bishop_left'].setPos(2 * SCALE, 0)
        self.pieces[f'black_bishop_right'].setPos(5 * SCALE, 0)
        self.pieces[f'black_knight_left'].setPos(1 * SCALE, 0)
        self.pieces[f'black_knight_right'].setPos(6 * SCALE, 0)

    def remove_all(self):
        for piece in self.pieces.values():
            self.scene.removeItem(piece)

    def findPieceName(self, searched_piece):
        for name, piece in self.pieces.items():
            if piece == searched_piece:
                return name
        return None

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:

            # Sprawdzamy, czy kliknięto na figurę
            item = self.itemAt(event.pos())
            if(isinstance(item, ChessPiece) and ((game.move_counter % 2 == 0 and item.color == 'white') or (game.move_counter % 2 == 1 and item.color == 'black'))):
                move_color_check = True
            else:
                move_color_check = False

            if isinstance(item, ChessPiece) and move_color_check:
                self.current_piece = item
                # Pobieramy możliwe ruchy dla klikniętej figury
                possible_moves = self.current_piece.get_possible_moves()
                # Dodajemy znaczniki dla każdego możliwego ruchu
                for move in possible_moves:
                    marker = QGraphicsPixmapItem(QPixmap('marker.png'))
                    marker.setPos(move[0], move[1])
                    marker.setOpacity(0.7)
                    self.scene.addItem(marker)
                    self.current_piece.markers.append(marker)

        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            # Usuwamy wszystkie znaczniki z poprzedniego kliknięcia
            for piece in self.pieces.values():
                for marker in piece.markers:
                    self.scene.removeItem(marker)
                piece.markers = []  # Resetujemy listę znaczników dla każdej figury
            
        # self.updateAttackedSquares()

        super().mouseReleaseEvent(event)

    def updateAttackedSquares(self):
        self.white_attacked_squares.clear()
        self.black_attacked_squares.clear()
        for piece in self.pieces.values():
            if piece.color == 'white':
                if isinstance(piece, Pawn):
                    self.white_attacked_squares.extend(piece.get_possible_takings())
                else:
                    self.white_attacked_squares.extend(piece.get_possible_moves())
            else:
                if isinstance(piece, Pawn):
                    self.black_attacked_squares.extend(piece.get_possible_takings())
                else:
                    self.black_attacked_squares.extend(piece.get_possible_moves())
        
        if (3*SCALE, 7*SCALE) in self.black_attacked_squares:
            self.d1_attacked = True
        else:
            self.d1_attacked = False
        if (5*SCALE, 7*SCALE) in self.black_attacked_squares:
            self.f1_attacked = True
        else:
            self.f1_attacked = False
        if (5*SCALE, 0) in self.white_attacked_squares:
            self.f8_attacked = True
        else:
            self.f8_attacked = False
        if (3*SCALE, 0) in self.white_attacked_squares:
            self.d8_attacked = True
        else:
            self.d8_attacked = False
  
    def addPiece(self, piece_type, pos):
        if game.move_counter % 2 == 1:
            color = 'black'
        else:
            color = 'white'

        if piece_type == 'Queen':
            self.pieces[f'new_{color}_{piece_type}_{game.move_counter}'] = Queen(color, 0, 0)
        if piece_type == 'Rook':
            self.pieces[f'new_{color}_{piece_type}_{game.move_counter}'] = Rook(color, 0, 0)
        if piece_type == 'Bishop':
            self.pieces[f'new_{color}_{piece_type}_{game.move_counter}'] = Bishop(color, 0, 0)
        if piece_type == 'Knight':
            self.pieces[f'new_{color}_{piece_type}_{game.move_counter}'] = Knight(color, 0, 0)


        new_piece = self.pieces[f'new_{color}_{piece_type}_{game.move_counter}']
        self.scene.addChessPiece(new_piece, 0, 0)
        new_piece.setPos(pos[0], pos[1])
        QTest.mouseClick(self.viewport(), Qt.LeftButton, pos=QPoint(50, 50)) #symulacja kliknięcia myszką w figurę - inaczej był problem z przesuwaniem - pojawiała się w 0, 0  w momencie kliknięcia

    def makeMoveAI(self): #faworyzuje bicie figur
        moves_list = []
        moves_list_cord = []
        letters = ['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h']
        numbers = [8, 7, 6, 5, 4, 3, 2, 1]
        if not game.mate_end:
            for piece in game.chess_view.pieces.values():
                if (piece.color == 'black'):
                    possible_moves = piece.get_possible_moves()
                    for move in possible_moves:
                        moves_list.append(f"{letters[int(piece.x()//SCALE)]}{numbers[int(piece.y()//SCALE)]}-{letters[int(move[0]//SCALE)]}{numbers[int(move[1]//SCALE)]}")
                        moves_list_cord.append([move[0], move[1]])
            rand_value = random.randint(0, len(moves_list)-1)
            random_move = moves_list[rand_value]


            target_item = self.scene.itemAt(moves_list_cord[rand_value][0] + SCALE//2, moves_list_cord[rand_value][1] + SCALE//2, QGraphicsView().transform())
            i = 0
            while not((isinstance(target_item, ChessPiece) and game.move_by_text(random_move))  or i >= len(moves_list)):
                rand_value -= 1
                random_move = moves_list[rand_value]
                target_item = self.scene.itemAt(moves_list_cord[rand_value][0] + SCALE//2, moves_list_cord[rand_value][1] + SCALE//2, QGraphicsView().transform())
                i += 1

            if not isinstance(target_item, ChessPiece):
                rand_value = random.randint(0, len(moves_list)-1)
                random_move = moves_list[rand_value]
                while not game.move_by_text(random_move):
                    rand_value -= 1
                    random_move = moves_list[random.randint(0, len(moves_list)-1)]
            
            for i in range(8):
                for j in range(8):
                    QTest.mouseClick(self.viewport(), Qt.LeftButton, pos=QPoint(i * SCALE + 50, j * SCALE + 50)) #symulacja kliknięcia myszką w figurę - inaczej był problem z przesuwaniem - pojawiała się w 0, 0  w momencie kliknięcia

    def makeMoveAI2(self):
        moves_list = []
        moves_list_cord = []
        letters = ['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h']
        numbers = [8, 7, 6, 5, 4, 3, 2, 1]
        best_move = 0
        best_move_rate = 0
        if not game.mate_end:
            for piece in game.chess_view.pieces.values():
                if (piece.color == 'black'):
                    possible_moves = piece.get_possible_moves()
                    for move in possible_moves:
                        moves_list.append(f"{letters[int(piece.x()//SCALE)]}{numbers[int(piece.y()//SCALE)]}-{letters[int(move[0]//SCALE)]}{numbers[int(move[1]//SCALE)]}")
                        moves_list_cord.append([move[0], move[1]])
            rand_value = random.randint(0, len(moves_list)-1)
            random_move = moves_list[rand_value]


            i = 0
            white_value, black_value = self.count_pieces_values()
            while i < len(moves_list):
                rand_value -= 1
                random_move = moves_list[rand_value]
                target_item  = self.scene.itemAt(moves_list_cord[rand_value][0] + SCALE//2, moves_list_cord[rand_value][1] + SCALE//2, QGraphicsView().transform())
                if isinstance(target_item, ChessPiece):
                    print("Możliwe bicie")
                    print(white_value, black_value)
                    print(self.piece_value(target_item))
                    move_rate = (white_value - self.piece_value(target_item))
                else:
                    move_rate = white_value
                if move_rate < best_move_rate:
                    best_move = random_move
                i += 1
            print(best_move)
            game.move_by_text(best_move)
            
            for i in range(8):
                for j in range(8):
                    QTest.mouseClick(self.viewport(), Qt.LeftButton, pos=QPoint(i * SCALE + 50, j * SCALE + 50)) #symulacja kliknięcia myszką w figurę - inaczej był problem z przesuwaniem - pojawiała się w 0, 0  w momencie kliknięcia

    def count_pieces_values(self):
        white_value = 0
        black_value = 0
        for piece in self.pieces.values():
            if piece.color == 'white':
                if isinstance(piece, Pawn):
                    white_value += 1
                elif isinstance(piece, Bishop) or isinstance(piece, Knight):
                    white_value += 3
                elif isinstance(piece, Rook):
                    white_value += 5
                elif isinstance(piece, Queen):
                    white_value += 9
            else:
                if isinstance(piece, Pawn):
                    black_value += 1
                elif isinstance(piece, Bishop) or isinstance(piece, Knight):
                    black_value += 3
                elif isinstance(piece, Rook):
                    black_value += 5
                elif isinstance(piece, Queen):
                    black_value += 9
        return white_value, black_value

    def piece_value(self, piece):
        value = 0
        if isinstance(piece, Pawn):
            value += 1
        elif isinstance(piece, Bishop) or isinstance(piece, Knight):
            value += 3
        elif isinstance(piece, Rook):
            value += 5
        elif isinstance(piece, Queen):
            value += 9
        return value
            


class ChessBoard(QGraphicsScene):
    def __init__(self):
        super().__init__()
        self.setSceneRect(0, 0, 8 * SCALE, 8 * SCALE)
        self.drawChessBoard()

    def drawChessBoard(self):
        # Load image of the chessboard
        image = QPixmap('chessboard.png')
        self.addPixmap(image)

    def addChessPiece(self, piece, x, y):
        self.addItem(piece)
        piece.setPos(x, y)

    def closestEmptySquare(self, piece):
        mouseX, mouseY = piece.scenePos().x(), piece.scenePos().y()
        col = round(mouseX / SCALE)
        row = round(mouseY / SCALE)
        pos = (col * SCALE, row * SCALE)
        return pos

class ChessPiece(QGraphicsPixmapItem):
    def __init__(self, pixmap, x, y, color):
        super().__init__(pixmap)
        self.setPos(x, y)
        self.setScale(SCALE/100)
        self.originalPos = None
        self.setFlag(QGraphicsPixmapItem.ItemIsMovable)
        self.setAcceptHoverEvents(True)
        self.setOpacity(1.0)
        self.color = color
        self.markers = []  # Lista znaczników dla możliwych ruchów


        # self.currentX = x * SCALE
        # self.currentY = y * SCALE

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.originalPos = self.pos()
            self.setOpacity(0.3)

            # Store potential moves
            self.possible_moves = self.get_possible_moves()

        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        move = ""
        promotion_flag = False
        mate = False
        if event.button() == Qt.LeftButton:
            self.setOpacity(1.0)

            # Check if released position is valid
            targetPos = self.scene().closestEmptySquare(self)
            if (targetPos in self.possible_moves) and ((game.move_counter % 2 == 0 and self.color == 'white') or (game.move_counter % 2 == 1 and self.color == 'black')): # możliwość ruchu dla odpowiedniego gracza
                self.setPos(-100, -100) # przeniesienie figury aby nie wykryło samej siebie przy warunku bicia
                target_item = self.scene().itemAt(targetPos[0] + SCALE//2, targetPos[1] + SCALE//2, QGraphicsView().transform())
                target_item_copy = target_item #kopia do ewentualnego cofnięcia niedozwolonego ruchu w przypadku

                self.setPos(targetPos[0], targetPos[1])
                if isinstance(target_item, ChessPiece): # warunek usunięcia figury przy biciu
                    self.scene().removeItem(target_item)
                elif isinstance(self, Pawn) and targetPos[0] != int(self.originalPos.x()):
                    target_item = self.scene().itemAt(game.chess_view.pawn_that_double_jumped_pos[0] + SCALE//2, game.chess_view.pawn_that_double_jumped_pos[1] + SCALE//2, QGraphicsView().transform())
                    target_item_copy = target_item
                    if isinstance(target_item, ChessPiece): # warunek usunięcia figury przy en passant
                        self.scene().removeItem(target_item)

                game.chess_view.updateAttackedSquares()
                

                white_king_pos = (game.chess_view.pieces['white_king'].x(), game.chess_view.pieces['white_king'].y())
                black_king_pos = (game.chess_view.pieces['black_king'].x(), game.chess_view.pieces['black_king'].y())
                #warunki ruchu królem na bite pole
                if not ((game.move_counter % 2 == 0 and white_king_pos in game.chess_view.black_attacked_squares) or (game.move_counter % 2 == 1 and black_king_pos in game.chess_view.white_attacked_squares)):
                    
                    if game.chess_view.white_long_castling_possibility and game.chess_view.findPieceName(self) == 'white_king' and targetPos == (2 * SCALE, 7 * SCALE):
                        game.chess_view.pieces['white_rook_left'].setPos(3 * SCALE, 7 * SCALE)
                    elif game.chess_view.white_short_castling_possibility and game.chess_view.findPieceName(self) == 'white_king' and targetPos == (6 * SCALE, 7 * SCALE):
                        game.chess_view.pieces['white_rook_right'].setPos(5 * SCALE, 7 * SCALE)
                    elif game.chess_view.black_long_castling_possibility and game.chess_view.findPieceName(self) == 'black_king' and targetPos == (2 * SCALE, 0):
                        game.chess_view.pieces['black_rook_left'].setPos(3 * SCALE, 0)
                    elif game.chess_view.black_short_castling_possibility and game.chess_view.findPieceName(self) == 'black_king' and targetPos == (6 * SCALE, 0):
                        game.chess_view.pieces['black_rook_right'].setPos(5 * SCALE, 0)

                    letters = ['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h']
                    numbers = [8, 7, 6, 5, 4, 3, 2, 1]
                    move = f"{letters[int(self.originalPos.x()//SCALE)]}{numbers[int(self.originalPos.y()//SCALE)]}-{letters[int(targetPos[0]//SCALE)]}{numbers[int(targetPos[1]//SCALE)]}"

                    game.logger = game.logger + f"\n{move}"
                    game.moves = game.moves + f"\n{move}"
                    if game.game_mode == "Online":
                        game.send_message(f"{move}")

                    header = "Chessgame " + "1"
                    moves = f"\n{move}"
                    # game.save_game_history(header, moves)
                    # game.save_game_history_to_xml(header, moves)


                    if isinstance(self, Pawn) and self.y() in [0, 7 * SCALE]:
                        promotion_piece_type = self.promotion()
                        game.chess_view.addPiece(promotion_piece_type, targetPos) #promocja piona
                        promotion_flag = True
                        move = f"promotion-{promotion_piece_type}"

                        game.logger = game.logger + f"\n{move}"
                        game.moves = game.moves + f"\n{move}"
                        if game.game_mode == "Online":
                            game.send_message(f"{move}")

                        header = "Chessgame " + "1"
                        moves = f"\n{move}"
                        # game.save_game_history(header, moves)
                        # game.save_game_history_to_xml(header, moves)



                    moved_piece = game.chess_view.findPieceName(self) #znajdowanie nazwy figury
                    removed_piece = game.chess_view.findPieceName(target_item_copy)
                    self.castling_possibility(moved_piece, removed_piece) #aktualizacja warunków roszady
                    
                    if isinstance(self, Pawn) and abs(targetPos[1] - self.originalPos.y()) == 2 * SCALE: #sprawdzenie czy pion przeskoczył o 2 pola
                        game.chess_view.pawn_that_double_jumped_pos = targetPos
                    else:
                        game.chess_view.pawn_that_double_jumped_pos = None

                    # warunki szacha - mata
                    if(white_king_pos in game.chess_view.black_attacked_squares or black_king_pos in game.chess_view.white_attacked_squares):
                        mate = self.mate()
                        #sprawdzenie mata
                        if mate:
                            game.stopTimers()
                            if game.move_counter % 2 == 0:
                                game.logger = game.logger + f"\nMate - White wins"
                            else:
                                game.logger = game.logger + f"\nMate - Black wins"
                            game.mate_end = True
                        else:
                            game.logger = game.logger + f"\nCheck"
                    elif self.mate():
                            game.stopTimers()
                            game.logger = game.logger + f"\nPat"
                            game.mate_end = True
                        

                    game.move_counter += 1
                    game.text_field.setPlainText(game.logger)
                    if not game.mate_end:
                        game.startTimers()
                    # game.chess_view.pieces['white_rook_left'].setPos(3 * SCALE, 7 * SCALE)

                    if promotion_flag:
                        self.scene().removeItem(self)

                    if game.game_mode == "AI":
                        game.chess_view.makeMoveAI()
                    elif game.game_mode == "AI2":
                        game.chess_view.makeMoveAI2()


                else: #kiedy król staje na atakowanym polu
                    self.setPos(self.originalPos) 
                    game.chess_view.updateAttackedSquares()
                    self.scene().addItem(target_item_copy)
            else:
                # Move back to original position if released position is invalid
                self.setPos(self.originalPos)
        
        super().mouseReleaseEvent(event)
    
    def mate(self):
        for piece in game.chess_view.pieces.values():
            if ((game.move_counter % 2 == 0 and self.color == 'white') or (game.move_counter % 2 == 1 and self.color == 'black')):
                possible_moves = piece.get_possible_moves()
                for move in possible_moves:
                    if self.move_emulation(piece, move) == True:
                        return False
        return True

    def move_emulation(self, piece, emulation_pos):
        orgPos = QPointF(piece.x(), piece.y())
        if ((game.move_counter % 2 == 1 and piece.color == 'white') or (game.move_counter % 2 == 0 and piece.color == 'black')):
                piece.setPos(-100, -100) # przeniesienie figury aby nie wykryło samej siebie przy warunku bicia
                target_item = self.scene().itemAt(emulation_pos[0] + SCALE/2, emulation_pos[1] + SCALE/2, QGraphicsView().transform())
                target_item_copy = target_item #kopia do ewentualnego cofnięcia niedozwolonego ruchu w przypadku


                # zbijana_figura = game.chess_view.findPieceName(target_item) # przykład znajdowania nazwy figury
                # print(zbijana_figura)

                piece.setPos(emulation_pos[0], emulation_pos[1])
                if isinstance(target_item, ChessPiece): # warunek usunięcia figury przy biciu
                    piece.scene().removeItem(target_item)
                game.chess_view.updateAttackedSquares()

                

                # działa tylko kiedy król wchodzi pod szacha
                white_king_pos = (game.chess_view.pieces['white_king'].x(), game.chess_view.pieces['white_king'].y())
                black_king_pos = (game.chess_view.pieces['black_king'].x(), game.chess_view.pieces['black_king'].y())
                if ((game.move_counter % 2 == 1 and white_king_pos in game.chess_view.black_attacked_squares) or (game.move_counter % 2 == 0 and black_king_pos in game.chess_view.white_attacked_squares)):
                    piece.setPos(orgPos) 
                    game.chess_view.updateAttackedSquares()
                    if isinstance(target_item_copy, ChessPiece):
                        piece.scene().addItem(target_item_copy)
                    return False
                else:
                    piece.setPos(orgPos) 
                    game.chess_view.updateAttackedSquares()
                    if isinstance(target_item_copy, ChessPiece):
                        piece.scene().addItem(target_item_copy)
                    return True
                
    def castling_possibility(self, moved_piece, removed_piece):
        if moved_piece == 'white_rook_left' or removed_piece == 'white_rook_left':
            game.chess_view.white_long_castling_possibility = False
        if moved_piece == 'white_rook_right' or removed_piece == 'white_rook_right':
            game.chess_view.white_short_castling_possibility = False
        if moved_piece == 'black_rook_left' or removed_piece == 'black_rook_left':
            game.chess_view.black_long_castling_possibility = False
        if moved_piece == 'black_rook_right' or removed_piece == 'black_rook_right':
            game.chess_view.black_short_castling_possibility = False
        if moved_piece == 'white_king':
            game.chess_view.white_short_castling_possibility = False
            game.chess_view.white_long_castling_possibility = False
        if moved_piece == 'black_king':
            game.chess_view.black_short_castling_possibility = False
            game.chess_view.black_long_castling_possibility = False
        
    def hoverEnterEvent(self, event):
        self.setOpacity(0.8)

    def hoverLeaveEvent(self, event):
        self.setOpacity(1.0)

    def promotion(self):
        promotion = Promotion()
        if promotion.exec_():
            chosen_piece = promotion.mode_combo_box.currentText()
        return chosen_piece


class King(ChessPiece):
    def __init__(self, color, x, y):
        if color == 'white':
            pixmap = QPixmap('figury/white_king.png')
        else:
            pixmap = QPixmap('figury/black_king.png')
        super().__init__(pixmap, x, y, color)
        

    def get_possible_moves(self):
        possible_moves = []
        current_col = int(self.x()) // SCALE
        current_row = int(self.y()) // SCALE

        # Generate possible moves for king
        for col_offset in range(-1, 2):
            for row_offset in range(-1, 2):
                col = current_col + col_offset
                row = current_row + row_offset
                if col >= 0 and col < 8 and row >= 0 and row < 8 and (col_offset != 0 or row_offset != 0):
                    possible_moves.append((col * SCALE, row * SCALE))

        possible_moves_temp = possible_moves
        possible_moves = []
        if self.scene() is not None:
            for move in possible_moves_temp:
                target_item = self.scene().itemAt(move[0] + SCALE/2, move[1] + SCALE/2, QGraphicsView().transform())
                if target_item is not None and (not isinstance(target_item, ChessPiece) or target_item.color != self.color):
                    possible_moves.append(move)

        #roszada biała
        if game.chess_view.white_long_castling_possibility and self.color == 'white':
            if (not isinstance(self.scene().itemAt(SCALE + SCALE/2, 7 * SCALE + SCALE/2, QGraphicsView().transform()), ChessPiece)) and (not isinstance(self.scene().itemAt(2 * SCALE + SCALE/2, 7 * SCALE + SCALE/2, QGraphicsView().transform()), ChessPiece)) and (not isinstance(self.scene().itemAt(3 * SCALE + SCALE/2, 7 * SCALE + SCALE/2, QGraphicsView().transform()), ChessPiece)):
                if not game.chess_view.d1_attacked:
                    possible_moves.append((2 * SCALE, 7 * SCALE))
        if game.chess_view.white_short_castling_possibility and self.color == 'white':
            if (not isinstance(self.scene().itemAt(5*SCALE + SCALE/2, 7 * SCALE + SCALE/2, QGraphicsView().transform()), ChessPiece)) and (not isinstance(self.scene().itemAt(6 * SCALE + SCALE/2, 7 * SCALE + SCALE/2, QGraphicsView().transform()), ChessPiece)):
                if not game.chess_view.f1_attacked:
                    possible_moves.append((6 * SCALE, 7 * SCALE))
        #roszada czarna
        if game.chess_view.black_long_castling_possibility and self.color == 'black':
            if (not isinstance(self.scene().itemAt(SCALE + SCALE/2, SCALE/2, QGraphicsView().transform()), ChessPiece)) and (not isinstance(self.scene().itemAt(2 * SCALE + SCALE/2, SCALE/2, QGraphicsView().transform()), ChessPiece)) and (not isinstance(self.scene().itemAt(3 * SCALE + SCALE/2, SCALE/2, QGraphicsView().transform()), ChessPiece)):
                if not game.chess_view.d8_attacked:
                    possible_moves.append((2 * SCALE, 0))
        if game.chess_view.black_short_castling_possibility and self.color == 'black':
            if (not isinstance(self.scene().itemAt(5*SCALE + SCALE/2, SCALE/2, QGraphicsView().transform()), ChessPiece)) and (not isinstance(self.scene().itemAt(6 * SCALE + SCALE/2, SCALE/2, QGraphicsView().transform()), ChessPiece)):
                if not game.chess_view.f8_attacked:
                    possible_moves.append((6 * SCALE, 0))

        return possible_moves

class Queen(ChessPiece):
    def __init__(self, color, x, y):
        if color == 'white':
            pixmap = QPixmap('figury/white_queen.png')
        else:
            pixmap = QPixmap('figury/black_queen.png')
        super().__init__(pixmap, x, y, color)

    def get_possible_moves(self):
        possible_moves = []
        current_col = int(self.x()) // SCALE
        current_row = int(self.y()) // SCALE

        # Generate possible moves for queen (combining moves of rook and bishop)
        for direction in [(1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (-1, -1), (-1, 1), (1, -1)]:
            col, row = current_col, current_row
            while True:
                col += direction[0]
                row += direction[1]
                if col < 0 or col >= 8 or row < 0 or row >= 8:
                    break
                possible_moves.append((col * SCALE, row * SCALE))
                # If there's a piece in the way, stop checking in this direction
                if self.scene() is not None:
                    if isinstance(self.scene().itemAt(col * SCALE + SCALE/2, row * SCALE + SCALE/2, QGraphicsView().transform()), ChessPiece):
                        break

        possible_moves_temp = possible_moves
        possible_moves = []
        if self.scene() is not None:
            for move in possible_moves_temp:
                target_item = self.scene().itemAt(move[0] + SCALE/2, move[1] + SCALE/2, QGraphicsView().transform())
                if target_item is not None and (not isinstance(target_item, ChessPiece) or target_item.color != self.color):
                    possible_moves.append(move)

        return possible_moves

class Rook(ChessPiece):
    def __init__(self, color, x, y):
        if color == 'white':
            pixmap = QPixmap('figury/white_rook.png')
        else:
            pixmap = QPixmap('figury/black_rook.png')
        super().__init__(pixmap, x, y, color)

    def get_possible_moves(self):
        possible_moves = []
        current_col = int(self.x()) // SCALE
        current_row = int(self.y()) // SCALE

        # Generate possible moves for rook
        for direction in [(1, 0), (-1, 0), (0, 1), (0, -1)]:
            col, row = current_col, current_row
            while True:
                col += direction[0]
                row += direction[1]
                if col < 0 or col >= 8 or row < 0 or row >= 8:
                    break
                possible_moves.append((col * SCALE, row * SCALE))
                # If there's a piece in the way, stop checking in this direction
                if self.scene() is not None:
                    if isinstance(self.scene().itemAt(col * SCALE + SCALE/2, row * SCALE + SCALE/2, QGraphicsView().transform()), ChessPiece):
                        break

        possible_moves_temp = possible_moves
        possible_moves = []
        if self.scene() is not None:
            for move in possible_moves_temp:
                target_item = self.scene().itemAt(move[0] + SCALE/2, move[1] + SCALE/2, QGraphicsView().transform())
                if target_item is not None and (not isinstance(target_item, ChessPiece) or target_item.color != self.color):
                    possible_moves.append(move)

        return possible_moves

class Bishop(ChessPiece):
    def __init__(self, color, x, y):
        if color == 'white':
            pixmap = QPixmap('figury/white_bishop.png')
        else:
            pixmap = QPixmap('figury/black_bishop.png')
        super().__init__(pixmap, x, y, color)

    def get_possible_moves(self):
        possible_moves = []
        current_col = int(self.x()) // SCALE
        current_row = int(self.y()) // SCALE

        # Generate possible moves for bishop
        for direction in [(1, 1), (-1, -1), (-1, 1), (1, -1)]:
            col, row = current_col, current_row
            while True:
                col += direction[0]
                row += direction[1]
                if col < 0 or col >= 8 or row < 0 or row >= 8:
                    break
                possible_moves.append((col * SCALE, row * SCALE))
                # If there's a piece in the way, stop checking in this direction
                if self.scene() is not None:
                    if isinstance(self.scene().itemAt(col * SCALE + SCALE/2, row * SCALE + SCALE/2, QGraphicsView().transform()), ChessPiece):
                        break

        possible_moves_temp = possible_moves
        possible_moves = []
        if self.scene() is not None:
            for move in possible_moves_temp:
                target_item = self.scene().itemAt(move[0] + SCALE/2, move[1] + SCALE/2, QGraphicsView().transform())
                if target_item is not None and (not isinstance(target_item, ChessPiece) or target_item.color != self.color):
                    possible_moves.append(move)

        return possible_moves

class Knight(ChessPiece):
    def __init__(self, color, x, y):
        if color == 'white':
            pixmap = QPixmap('figury/white_knight.png')
        else:
            pixmap = QPixmap('figury/black_knight.png')
        super().__init__(pixmap, x, y, color)

    def get_possible_moves(self):
        possible_moves = []
        current_col = int(self.x()) // SCALE
        current_row = int(self.y()) // SCALE

        # Generate possible moves for knight
        for col_offset in [-2, -1, 1, 2]:
            for row_offset in [-2, -1, 1, 2]:
                if abs(col_offset) != abs(row_offset):
                    col = current_col + col_offset
                    row = current_row + row_offset
                    if col >= 0 and col < 8 and row >= 0 and row < 8:
                        possible_moves.append((col * SCALE, row * SCALE))


        possible_moves_temp = possible_moves
        possible_moves = []
        if self.scene() is not None:
            for move in possible_moves_temp:
                target_item = self.scene().itemAt(move[0] + SCALE/2, move[1] + SCALE/2, QGraphicsView().transform())
                if target_item is not None and (not isinstance(target_item, ChessPiece) or target_item.color != self.color):
                    possible_moves.append(move)

        return possible_moves

class Pawn(ChessPiece):
    def __init__(self, color, x, y):
        if color == 'white':
            pixmap = QPixmap('figury/white_pawn.png')
        else:
            pixmap = QPixmap('figury/black_pawn.png')
        super().__init__(pixmap, x, y, color)

    def get_possible_moves(self):
        possible_moves = []
        current_col = int(self.x()) // SCALE
        current_row = int(self.y()) // SCALE
        if self.color == 'white':
            direction = -1  # Direction depends on pawn color
        else:
            direction = 1
        
        col, row = current_col, current_row
        row += direction
        # Regular pawn move
        if self.scene() is not None:
            if not isinstance(self.scene().itemAt(col * SCALE + SCALE/2, row * SCALE + SCALE/2, QGraphicsView().transform()), ChessPiece):
                possible_moves.append((col * SCALE, row * SCALE))
                if (not isinstance(self.scene().itemAt(col * SCALE + SCALE/2, (row + direction) * SCALE + SCALE/2, QGraphicsView().transform()), ChessPiece)) and (int(self.y()) // SCALE == 1 or int(self.y()) // SCALE == 6):
                    possible_moves.append((col * SCALE, (row + direction) * SCALE))

        # Capture move
        for col_offset in [-1, 1]:
            col += col_offset
            if col >= 0 and col < 8 and row >= 0 and row < 8:
                if self.scene() is not None:
                    target_piece = self.scene().itemAt(col * SCALE + SCALE/2, row * SCALE + SCALE/2, QGraphicsView().transform())
                    if isinstance(target_piece, ChessPiece) and target_piece.color != self.color:
                        possible_moves.append((col * SCALE, row * SCALE))
            col -= col_offset

        #En passant
        if game.chess_view.pawn_that_double_jumped_pos is not None:
            if game.chess_view.pawn_that_double_jumped_pos[1] == int(self.y()) and self.color == 'white':
                if game.chess_view.pawn_that_double_jumped_pos[0] == int(self.x()) - SCALE:
                    possible_moves.append((int(self.x()) - SCALE, int(self.y()) - SCALE))
                elif game.chess_view.pawn_that_double_jumped_pos[0] == int(self.x()) + SCALE:
                    possible_moves.append((int(self.x()) + SCALE, int(self.y()) - SCALE))

            elif game.chess_view.pawn_that_double_jumped_pos[1] == int(self.y()) and self.color == 'black':
                if game.chess_view.pawn_that_double_jumped_pos[0] == int(self.x()) - SCALE:
                    possible_moves.append((int(self.x()) - SCALE, int(self.y()) + SCALE))
                elif game.chess_view.pawn_that_double_jumped_pos[0] == int(self.x()) + SCALE:
                    possible_moves.append((int(self.x()) + SCALE, int(self.y()) + SCALE))

            

        return possible_moves
    

    def get_possible_takings(self):
        possible_takings = []
        current_col = int(self.x()) // SCALE
        current_row = int(self.y()) // SCALE
        if self.color == 'white':
            direction = -1  # Direction depends on pawn color
        else:
            direction = 1
        
        col, row = current_col, current_row
        row += direction

        # Capture move
        for col_offset in [-1, 1]:
            col += col_offset
            if col >= 0 and col < 8 and row >= 0 and row < 8:
                if self.scene() is not None:
                    target_piece = self.scene().itemAt(col * SCALE + SCALE/2, row * SCALE + SCALE/2, QGraphicsView().transform())
                    if isinstance(target_piece, ChessPiece) and target_piece.color != self.color:
                        possible_takings.append((col * SCALE, row * SCALE))
                    elif isinstance(target_piece, ChessPiece):
                        pass
                    else:
                        possible_takings.append((col * SCALE, row * SCALE))
            col -= col_offset
            
                #En passant
        if game.chess_view.pawn_that_double_jumped_pos is not None:
            if game.chess_view.pawn_that_double_jumped_pos[1] == int(self.y()) and self.color == 'white':
                if game.chess_view.pawn_that_double_jumped_pos[0] == int(self.x()) - SCALE:
                    possible_takings.append((int(self.x()) - SCALE, int(self.y()) - SCALE))
                elif game.chess_view.pawn_that_double_jumped_pos[0] == int(self.x()) + SCALE:
                    possible_takings.append((int(self.x()) + SCALE, int(self.y()) - SCALE))
                    
            elif game.chess_view.pawn_that_double_jumped_pos[1] == int(self.y()) and self.color == 'black':
                if game.chess_view.pawn_that_double_jumped_pos[0] == int(self.x()) - SCALE:
                    possible_takings.append((int(self.x()) - SCALE, int(self.y()) + SCALE))
                elif game.chess_view.pawn_that_double_jumped_pos[0] == int(self.x()) + SCALE:
                    possible_takings.append((int(self.x()) + SCALE, int(self.y()) + SCALE))


        return possible_takings

if __name__ == '__main__':
    app = QApplication(sys.argv)
    game = ChessGame()
    game.show()
    sys.exit(app.exec_())
