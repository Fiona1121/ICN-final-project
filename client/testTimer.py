# from multiprocessing import Event
# from threading import Thread, Timer
# from time import sleep, time
import struct

# # class Timer(Thread):
# #     def __init__(self):
# #         Thread.__init__(self)
# #         self.event = Event()
# #         self.count = 10

# #     def run(self):
# #         while self.count > 0 and not self.event.is_set():
# #             print(self.count)
# #             self.count -= 1
# #             self.event.wait(1)

# #     def stop(self):
# #         self.event.set()
# def printline():
#     print("timer")


# timer = Timer(5, printline)
# timer.start()
# while True:
#     print("true")
#     sleep(10)
#     timer.cancel()

# round(time() * 100)  # get current time in millis
fraction_lost = 0.0242
cumulative_lost = 12
high_seq_num = 80
struct.pack("fII", fraction_lost, cumulative_lost, high_seq_num)

from PIL import Image
from io import BytesIO

with open("test.jpeg", "rb") as image:
    f = image.read()
    img = Image.open(BytesIO(f))
    output = Image.new(img.mode, img.size)
    img.save("output.jpeg", format="JPEG", optimize=True, quality=80)
    print(output)
