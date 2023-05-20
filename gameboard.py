from kivy.app import App
from kivy.uix.label import Label
from kivy.uix.gridlayout import GridLayout
from kivy.uix.scatter import Scatter
from kivy.graphics import Rectangle, Color 
from kivy.uix.widget import Widget
from kivy.core.window import Window

# Chess engine imports
import os
import gameboard
import SSIM_PIL as ssim
import chess
import cv2

class ChessGame():
    fenGameState = ""

    def __init__(self, **kwargs):
        self.fenGameState = gameboard.ChessBoardUI.fen()

    # def get_valid_moves():
    #     print(chess



    # @staticmethod
    # def initialize_chess_images_cache():
    #     currentBoardImage = main.Board.get_board_as_CV2()
    #     cv2.imshow("temp.png", currentBoardImage)

    #     # List of pieces in initial chessboard order
    #     piece_order = ['rook', 'knight', 'bishop', 'queen', 'king', 'bishop', 'knight', 'rook'] + ['pawn']*8 + ['']*32 + ['pawn']*8 + ['rook', 'knight', 'bishop', 'queen', 'king', 'bishop', 'knight', 'rook']

    #     # Get the tiles from the slice function
    #     tiles = main.Board.slice(8, currentBoardImage)

    #     # Ensure there are 64 pieces
    #     assert len(tiles) == len(piece_order), "Number of tiles does not match the number of chess pieces"

    #     # Create the cache/chess directory if it doesn't exist
    #     directory = "cache/chess"
    #     if not os.path.exists(directory):
    #         os.makedirs(directory)

    #     # Save each non-empty tile with the corresponding piece name
    #     for idx, tile in enumerate(tiles):
    #         if piece_order[idx] != '':
    #             tile_name = piece_order[idx] + '_black' if idx < 32 else piece_order[idx] + '_white'
    #             filename = f"{directory}/{tile_name}.png"
    #             print(filename)
    #             cv2.imwrite(filename, tile) 


class DraggableChessPiece(Scatter):
    def __init__(self, text, chess_board, **kwargs):
        super(DraggableChessPiece, self).__init__(**kwargs)
        self.label = Label(text=text, size=self.size, font_size=self.size[0] / 2, color=(1, 0, 0, 1))  # RGB for red and 1 for opacity
        self.add_widget(self.label)
        self.chess_board = chess_board
        self.origin = None
        self.offset = (0, 0)  # Store the offset between the touch position and the piece position

    def collide_point(self, x, y):
        return super(DraggableChessPiece, self).collide_point(x, y)

    def on_touch_down(self, touch):
        if self.collide_point(*touch.pos):
            self.origin = self.pos  # Store the original piece position
        return super(DraggableChessPiece, self).on_touch_down(touch)

    def on_touch_move(self, touch):
        if self.origin:
            self.center_x = touch.pos[0]  # Move the piece along with the touch position
            self.center_y = touch.pos[1]
        return super(DraggableChessPiece, self).on_touch_move(touch)

    def on_touch_up(self, touch):
        if True:
            pass




        if self.origin:
            square_size = self.chess_board.square_size
            self.x = round((self.x) / square_size) * square_size
            self.y = round((self.y) / square_size) * square_size

            # Calculate the old position of the piece in the piece layout
            old_row = int((self.origin[1] + square_size / 2) // square_size)
            old_col = int((self.origin[0] + square_size / 2) // square_size)
            piece_layout = self.chess_board.piece_layout

            # Remove the piece from the old position in the piece layout
            piece_layout[7 - old_row][old_col] = " "

            # Calculate the new position of the piece in the piece layout
            new_row = int((self.y + square_size / 2) // square_size)
            new_col = int((self.x + square_size / 2) // square_size)

            # Ensure the new position is within the board boundaries
            new_row = max(0, min(new_row, 7))
            new_col = max(0, min(new_col, 7))

            # Update the piece layout based on the new position of the piece
            piece_layout[7 - new_row][new_col] = self.label.text

            # Print the updated piece layout
            for row in piece_layout:
                print(" ".join(row))

        self.origin = None
        return super(DraggableChessPiece, self).on_touch_up(touch)


class ChessBoardUI(Widget):
    def __init__(self, square_size, **kwargs):
        super(ChessBoardUI, self).__init__(**kwargs)
        self.cols = 8
        self.rows = 8
        self.square_size = square_size
        self.squares = []
        self.piece_layout = [
            list("rnbqkbnr"),
            list("pppppppp"),
            list("        "),
            list("        "),
            list("        "),
            list("        "),
            list("PPPPPPPP"),
            list("RNBQKBNR"),
        ]
        for i in range(self.rows):
            for j in range(self.cols):
                color = [1, 1, 1, 1] if (i + j) % 2 == 0 else [0, 0, 0, 1]  # alternating colors for
                square = Button(pos=(j * self.square_size, i * self.square_size),
                                size=(self.square_size, self.square_size), background_color=color)
                self.squares.append(square)
                self.add_widget(square)
                if self.piece_layout[7 - i][j] != ' ':
                    piece = DraggableChessPiece(text=self.piece_layout[7 - i][j], chess_board=self, size=(self.square_size, self.square_size),
                                                pos=(j * self.square_size, i * self.square_size))
                    self.add_widget(piece)



    def fen(self):
        """
            Returns state of game on board in fen format.
        """
        empty = 0
        fen = ''
        for i in range(8):  # 8x8 board
            for j in range(8):  # iterate through files
                piece = self.piece_layout[i][j]
                if piece != ' ':  # if the square is not empty
                    if empty > 0:
                        fen += str(empty)
                        empty = 0
                    fen += piece
                else:
                    empty += 1

                if j == 7:  # end of the row
                    if empty > 0:
                        fen += str(empty)
                    if i != 7:  # if not the last row
                        fen += '/'
                    empty = 0
        return fen
    
    def ascii(self):
        s = '   +------------------------+\n'
        for i in range(8):  # 8x8 board
            s += ' ' + str(8 - i) + ' |'  # display the rank
            for j in range(8):  # iterate through files
                piece = self.piece_layout[i][j]
                s += ' ' + piece + ' '
            s += '|\n'

        s += '   +------------------------+\n'
        s += '     a  b  c  d  e  f  g  h'
        return s
    
class ChessApp(App):
    def build(self):
        chess_board = ChessBoardUI(40)
        Window.size = (chess_board.cols * chess_board.square_size, chess_board.rows * chess_board.square_size)
        return chess_board
    


if __name__ == "__main__":
    import chess
    print(chess.__version__)
    print(dir(chess))
    ChessApp().run()
