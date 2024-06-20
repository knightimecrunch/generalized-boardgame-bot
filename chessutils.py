import os
import cv2
import main


def initialize_chess_images_cache():
    currentBoardImage = main.Board.get_board_as_CV2()
    cv2.imshow("temp.png", currentBoardImage)

    # List of pieces in initial chessboard order
    piece_order = ['rook', 'knight', 'bishop', 'queen', 'king', 'bishop', 'knight', 'rook'] + ['pawn']*8 + ['']*32 + ['pawn']*8 + ['rook', 'knight', 'bishop', 'queen', 'king', 'bishop', 'knight', 'rook']

    # Get the tiles from the slice function
    tiles = main.Board.slice(8, currentBoardImage)

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