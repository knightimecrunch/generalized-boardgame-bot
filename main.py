# kivy imports
from kivy.app import App
from kivy.uix.label import Label
from kivy.uix.gridlayout import GridLayout
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.clock import Clock
from kivy.uix.image import Image as kvImage

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

# Buffer to hold current screen image
memoryBuffer = io.BytesIO() 
temp = Image.open("board.png")
temp.save(memoryBuffer, format='png')

# Setting Widget Types of Classes for Kvlang Declarations
class SettingsScreen(Screen):
    pass
class ChessToolsView(Screen):
    pass
class ToolBar(BoxLayout):
    pass
class ToolsScreenManager(ScreenManager):
    pass

# Game Types : Chess, Checkers*, GO*
# *not implemented

# Chess engine imports
import SSIM_PIL as ssim

class Chess():
    @staticmethod
    def initialize_chess_images_cache():
        # List of pieces in initial chessboard order
        piece_order = ['rook', 'knight', 'bishop', 'queen', 'king', 'bishop', 'knight', 'rook'] + ['pawn']*8 + ['empty']*32 + ['pawn']*8 + ['rook', 'knight', 'bishop', 'queen', 'king', 'bishop', 'knight', 'rook']

        # Get the tiles from the slice function
        tiles = Board.slice(8)

        # Ensure there are 64 pieces
        assert len(tiles) == len(piece_order), "Number of tiles does not match the number of chess pieces"

        # Save each tile with the corresponding piece name
        for idx, tile in enumerate(tiles):
            tile_name = piece_order[idx]
            print(f"cache/chess/{tile_name}_{idx}.png")
            cv2.imwrite(f"cache/chess/{tile_name}_{idx}.png", tile)

class Checkers():
    pass

class Go():
    pass

# App structure

class SplitBoardImagesView(GridLayout):
    main_instance = None
    def __init__(self, **kwargs):
        super(SplitBoardImagesView, self).__init__(**kwargs)
        self.cols = 1
        self.rows = 1

    def store(self):
        SplitBoardImagesView.main_instance = self

    def display_board(tiles, h, w):
        imageArray = SplitBoardImagesView.main_instance.ids["imageGrid"]
        imageArray.cols = w
        imageArray.rows = h
        imageArray.clear_widgets()
        for tile in tiles:
            tile = Board.openCVtoCoreImage(tile)
            imageArray.add_widget(kvImage(texture = tile.texture))

class Board:
    """
        Game-type agnostic class that manages off-screen board image data. 
    """
    lastCapture = cv2.imread("board.png")

    @staticmethod
    def update(object, dt):
        global memoryBuffer
        memoryBuffer.seek(0) #after writing return to 0 index of memory for reading
        captureCV2 = np.frombuffer(memoryBuffer.getvalue(), dtype=np.uint8)
        captureCV2 = cv2.imdecode(captureCV2, cv2.IMREAD_ANYCOLOR)
        if not(Board.is_identical(captureCV2, Board.lastCapture)):
            Board.lastCapture = captureCV2
            Board.processing(captureCV2)
            processedCapture = Board.draw_grid(captureCV2, (8,8))
            capture = Board.openCVtoCoreImage(processedCapture)
            object.texture = capture.texture

    @staticmethod
    def processing(boardImage):
        tileList = Board.slice(8, boardImage)
        SplitBoardImagesView.display_board(tileList, 8, 8)

    @staticmethod
    def is_identical(image1, image2):
        return image1.shape == image2.shape and not(np.bitwise_xor(image1,image2).any())

    @staticmethod
    def openCVtoCoreImage(anOpenCV):
        is_success, buffer = cv2.imencode(".png", anOpenCV)
        tempBuffer = io.BytesIO(buffer)
        tempBuffer.seek(0)
        aCoreImage = CoreImage(io.BytesIO(tempBuffer.read()), ext='png')
        tempBuffer.close()
        return aCoreImage
    
    @staticmethod
    def draw_grid(img, grid_shape, color = (0, 0, 255), thickness = 1):
        h, w, _ = img.shape
        rows, cols = grid_shape
        dy, dx = h / rows, w / cols
        for x in np.linspace(start = dx, stop = w - dx, num = cols - 1):
            x = int(round(x))
            cv2.line(img, (x, 0), (x, h), color=color, thickness=thickness)
        for y in np.linspace(start = dy, stop = h - dy, num = rows - 1):
            y = int(round(y))
            cv2.line(img, (0, y), (w, y), color = color, thickness = thickness)
        return img

    @staticmethod
    def slice(nslices, boardImage = lastCapture):
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

class BoardScreen(Screen):
    """
        Game-type agnostic class that manages on-screen board image data. 
    """
    def __init__(self, **kwargs):
        super(BoardScreen, self).__init__(**kwargs)

    def on_kv_post(self, base_widget): #event fires once kv has loaded
        Clock.schedule_interval(partial(Board.update, self.ids['boardImage']), 0.25)
        memoryBuffer.seek(0)
        capture = CoreImage(io.BytesIO(memoryBuffer.getvalue()), ext='png')
        self.ids['boardImage'].texture = capture.texture

class BoardView(App):
    topLeft = (0,0)
    botRight = (100,100)
    def update_capture(*args): 
        global memoryBuffer
        topLeft = BoardView.topLeft
        botRight = BoardView.botRight
        sct = mss.mss()
        width = abs(topLeft[0] - botRight[0]) 
        height = abs(topLeft[1] - botRight[1]) 
        bounding_box = {'top': topLeft[1], 'left': topLeft[0], 'width': width, 'height': height}
        image = sct.grab(bounding_box)
        image = Image.frombytes("RGB", image.size, image.bgra, "raw", "BGRX") 
        image.save(memoryBuffer, format='png') 

    def on_click(x, y, button, pressed):
        if pressed:
            BoardView.topLeft = (x, y)
        print('{0} at {1}'.format('Pressed' if pressed else 'Released', (x, y)))
        if not pressed:
            BoardView.botRight = (x,y)
            BoardView.update_capture()
            return False
        
    def start_listener(null): 
        with mouse.Listener(on_click=BoardView.on_click) as listener:
            listener.join() 
    def build(self):
        Clock.schedule_interval(BoardView.update_capture, 0.25)
        pass

if __name__ == '__main__':
    BoardView().run()


