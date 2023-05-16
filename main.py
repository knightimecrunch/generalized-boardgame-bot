# kivy imports
from kivy.app import App
from kivy.uix.label import Label
from kivy.uix.gridlayout import GridLayout
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.clock import Clock
from kivy.uix.image import Image as kvImage
from kivy.core.window import Window
from kivy.uix.tabbedpanel import TabbedPanel

# Screen capture imports, with goal of platform independance + multimonitor support
from functools import partial
from PIL import Image
from kivy.core.image import Image as CoreImage
from pynput import mouse
import mss
import mss.tools
import numpy as np
from kivy.graphics import texture
import io
import cv2
import os
from pathlib import Path

# Setting Widget Types of Classes for Kvlang Declarations
class SettingsScreen(Screen):
    pass
class ChessToolsView(Screen):
    pass
class ChessToolsTabsView(TabbedPanel):
    pass
class ToolBar(BoxLayout):
    pass
class ToolsScreenManager(ScreenManager):
    pass
class GameBoardView(BoxLayout):
    pass

# Game Types : Chess, Checkers*, GO*
# *not implemented

# Chess engine imports
import chessboard as ChessBoard
import SSIM_PIL as ssim

class Chess():
    @staticmethod
    def initialize_chess_images_cache():
        currentBoardImage = BoardViewport.get_board_as_CV2()
        cv2.imshow("temp.png", currentBoardImage)

        # List of pieces in initial chessboard order
        piece_order = ['rook', 'knight', 'bishop', 'queen', 'king', 'bishop', 'knight', 'rook'] + ['pawn']*8 + ['']*32 + ['pawn']*8 + ['rook', 'knight', 'bishop', 'queen', 'king', 'bishop', 'knight', 'rook']

        # Get the tiles from the slice function
        tiles = BoardViewport.slice(8, currentBoardImage)

        # Ensure there are 64 pieces
        assert len(tiles) == len(piece_order), "Number of tiles does not match the number of chess pieces"

        # Create the cache/chess directory if it doesn't exist
        directory = "cache/chess"
        if not os.path.exists(directory):
            os.makedirs(directory)

        # Save each non-empty tile with the corresponding piece name
        for idx, tile in enumerate(tiles):
            if piece_order[idx] != '':
                tile_name = piece_order[idx] + '_black' if idx < 32 else piece_order[idx] + '_white'
                filename = f"{directory}/{tile_name}.png"
                print(filename)
                cv2.imwrite(filename, tile)

class Checkers():
    pass

class Go():
    pass

# App structure

class ImageMatrixView(GridLayout):
    self = None

    def __init__(self, **kwargs):
        super(ImageMatrixView, self).__init__(**kwargs)
        ImageMatrixView.self = self
        self.cols = 1
        self.rows = 1

    def display_board(tiles, h, w):
        imageArray = ImageMatrixView.self.ids["imageGrid"]
        imageArray.cols = w
        imageArray.rows = h
        imageArray.clear_widgets()
        for tile in tiles:
            tile = BoardViewport.openCVtoCoreImage(tile)
            imageArray.add_widget(kvImage(texture = tile.texture))

class BoardViewport:
    """
        Game-type agnostic class that manages off-screen board image data. 
    """
    # Buffer to hold current screen image
    memoryBuffer = io.BytesIO() 
    temp = Image.open("board.png")
    temp.save(memoryBuffer, format='png')

    currentBoardImage = cv2.imread("board.png")
    
    # Coordinates for on-screen for board
    topLeft = (0, 0)
    botRight = (100, 100)

    def board_loop(dt):
        BoardViewport.write_screen_to_buffer()
        BoardViewport.redraw_board()

    def write_screen_to_buffer(*args):
        """
            Copies the contents of the screen from the top left bound to the bottom right bound to memory.
        """
        topLeft = BoardViewport.topLeft
        botRight = BoardViewport.botRight
        sct = mss.mss()
        width = abs(topLeft[0] - botRight[0]) 
        height = abs(topLeft[1] - botRight[1]) 
        bounding_box = {'top': topLeft[1], 'left': topLeft[0], 'width': width, 'height': height}
        image = sct.grab(bounding_box)
        image = Image.frombytes("RGB", image.size, image.bgra, "raw", "BGRX") 
        image.save(BoardViewport.memoryBuffer, format='png') 

    @staticmethod
    def redraw_board():
        """
            Redraws on-screen board, adding a grid, re-read from memory is require from conversion to CoreImage.
        """
        # reads into CV2 to make image adjustments, might be faster to read directly to CoreImage
        BoardViewport.memoryBuffer.seek(0) #after writing return to 0 index of memory for reading
        captureCV2 = np.frombuffer(BoardViewport.memoryBuffer.getvalue(), dtype=np.uint8)
        captureCV2 = cv2.imdecode(captureCV2, cv2.IMREAD_ANYCOLOR)
        BoardViewport.currentBoardImage = captureCV2

        # draw to sliced board view
        tileList = BoardViewport.slice(8, captureCV2)
        ImageMatrixView.display_board(tileList, 8, 8)

        # draw to board viewport
        processedCapture = BoardViewport.draw_grid(captureCV2, (8,8))
        capture = BoardViewport.openCVtoCoreImage(processedCapture)
        PrimaryScreen.set_board(capture.texture)

    @staticmethod
    def draw_grid(img, grid_shape, color = (0, 0, 255), thickness = 1):
        h, w, _ = img.shape
        rows, cols = grid_shape
        dy, dx = h / rows, w / cols
        for x in np.linspace(start = dx, stop = w - dx, num = cols - 1):
            x = int(round(x))
            cv2.line(img, (x, 0), (x, h), color = color, thickness = thickness)
        for y in np.linspace(start = dy, stop = h - dy, num = rows - 1):
            y = int(round(y))
            cv2.line(img, (0, y), (w, y), color = color, thickness = thickness)
        return img

    @staticmethod
    def slice(nslices, boardImage = currentBoardImage):
        h, w, channels = boardImage.shape
        slicesY = [(h // nslices) * n for n in range(1, nslices + 1)]
        slicesX = [(w // nslices) * n for n in range(1, nslices + 1)]
        tiles = []
        prevX = 0 
        prevY = 0
        for y in slicesY:
            row = boardImage[prevY:y, :]
            prevY = y
            prevX = 0
            for x in slicesX:
                tile = row[:, prevX:x]
                tiles.append(tile)
                prevX = x
        return tiles
    
    @staticmethod
    def openCVtoCoreImage(anOpenCV):
        is_success, buffer = cv2.imencode(".png", anOpenCV)
        tempBuffer = io.BytesIO(buffer)
        tempBuffer.seek(0)
        aCoreImage = CoreImage(io.BytesIO(tempBuffer.read()), ext='png')
        tempBuffer.close()
        return aCoreImage
    
    def get_board_as_CV2():
        BoardViewport.memoryBuffer.seek(0)
        captureCV2 = np.frombuffer(BoardViewport.memoryBuffer.getvalue(), dtype = np.uint8)
        return cv2.imdecode(captureCV2, cv2.IMREAD_ANYCOLOR)
    
    def get_board_as_CoreImage():
        BoardViewport.memoryBuffer.seek(0)
        return CoreImage(io.BytesIO(BoardViewport.memoryBuffer.read()), ext='png')

class PrimaryScreen(Screen):
    """
        Screen containing the board, the segmented board, and the menu for the selected game.
    """
    self = None

    def __init__(self, **kwargs):
        super(PrimaryScreen, self).__init__(**kwargs)
        PrimaryScreen.self = self

    def set_board(capture):
        PrimaryScreen.self.ids['boardImage'].texture = capture

class Application(App):
    gameType = "chess"

    def update_board_corners(x, y, button, pressed):
        if pressed:
            BoardViewport.topLeft = (x, y)
        print('{0} at {1}'.format('Pressed' if pressed else 'Released', (x, y)))
        if not pressed:
            BoardViewport.botRight = (x,y)
            BoardViewport.write_screen_to_buffer()
            return False
    
    def initialize_chess_images_cache(_):
        Chess.initialize_chess_images_cache()

    def start_click_and_drag(null): 
        with mouse.Listener(on_click=Application.update_board_corners) as listener:
            listener.join() 

    def build(self):
        self.title = "ChessBotYZ"
        # Window.set_system_cursor("cross")
        # Instead use whole screen imshow/cv2 then draw intersecting lines following cursor on that imshow
        if Application.gameType == "chess":
            print(PrimaryScreen.self.ids)
            PrimaryScreen.self.ids['gameBoardView'].children[0].add_widget(ChessBoard.ChessBoard(40))
        Clock.schedule_interval(BoardViewport.board_loop, 0.25)
        pass


if __name__ == '__main__':
    Application().run()


