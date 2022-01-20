import cv2
import numpy as np

import os


class VideoStream:
    DEFAULT_IMAGE_SHAPE = (480, 640)
    VIDEO_LENGTH = 500
    DEFAULT_FPS = 24


    MAX_DGRAM = 2**12 ## 2**16 original
    MAX_IMAGE_DGRAM = MAX_DGRAM - 64 # extract 64 bytes in case UDP frame overflown





    def __init__(self, file_path: str):

        if os.path.isfile(file_path):
            self._stream = cv2.VideoCapture(file_path) 
        else:    
            self._stream = cv2.VideoCapture(0)

        
        # frame number is zero-indexed
        # after first frame is sent, this is set to zero
        self.current_frame_number = -1

    def close(self):
        
        cv2.destroyAllWindows()
        #self._stream.close()

    def get_next_frame(self) -> bytes:

        videoframe = self._stream.read()[1]

        videoframe = cv2.imencode('.jpg',   videoframe )[1]
        videoframe = videoframe.tobytes()
        
        #videoframe = videoframe.tobytes()

        self.current_frame_number += 1

        return videoframe














