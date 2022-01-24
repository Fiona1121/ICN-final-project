# ICN-final-project
Final project for ICN Fall, 2021 at NTU

## Feature

- **Client Server Communication:** using the Real-Time Streaming Protocol (RTSP)
- **Real Time Streaming:** sending data using Realtime Transfer Protocol (RTP)
- **Quality of Service**: using Real-time Transport Control Protocol (RTCP) to communicate traffic condition
- **Object detection:** using Tensorflow to add detection while streaming
- **Camera Video Streaming**: transferring server camera video to client by RTSP
- **Lost Server Simulation:** assign a probability for server to loss a packet while sending RTP

## System Flow

![system-flow.jpeg](https://s3.us-west-2.amazonaws.com/secure.notion-static.com/97284814-6d7f-4e7a-b324-8b3f85567399/84AC54AE-DF79-4EB6-A5E6-141133733A00.jpeg?X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Content-Sha256=UNSIGNED-PAYLOAD&X-Amz-Credential=AKIAT73L2G45EIPT3X45%2F20220124%2Fus-west-2%2Fs3%2Faws4_request&X-Amz-Date=20220124T134232Z&X-Amz-Expires=86400&X-Amz-Signature=e587ce1802998cbc05d77cf361f450764d6fc2812e7b8307c4315040daacf1f7&X-Amz-SignedHeaders=host&response-content-disposition=filename%20%3D%2284AC54AE-DF79-4EB6-A5E6-141133733A00.jpeg%22&x-id=GetObject)

## Protocol

### RTP

RTP packet由UDP傳遞，負責將影像由Server端傳送至Client端。RTP packet將sequence number、 time stamp等資訊包進Header, frame 作為payload。由於以UDP傳送過大的packet容易產生socket.timeout的error，故將packet切成size為4096 bytes的segment傳送至clinet端。

### RTSP

RTSP由TCP傳送，負責將client端的四個指令SETUP、PLAY、PAUSE、TEARDOWN傳送到server端。當使用者在介面中點下四種按鈕時，會將對應動作的指令裝入RTSP封包，並傳送至server，server將讀出封包中對應的rtp port,並對其做出client 下達的指令。

### RTCP

RTCP由UDP傳遞，負責將封包傳送品質(fraction_lost)，傳送至Server端，Server端將以此之標計算出網路壅塞程度(Congestion_level)，並以網路壅塞程度控制傳送程度及壓縮影像品質。以避免網路壅塞。

![RTCP.jpeg](https://s3.us-west-2.amazonaws.com/secure.notion-static.com/67bbca42-525f-45ee-bed5-35debb967ae7/Untitled.png?X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Content-Sha256=UNSIGNED-PAYLOAD&X-Amz-Credential=AKIAT73L2G45EIPT3X45%2F20220124%2Fus-west-2%2Fs3%2Faws4_request&X-Amz-Date=20220124T134436Z&X-Amz-Expires=86400&X-Amz-Signature=da1765c83e431300471385a38d8e3088129eea4cedb138b3192000a1fb47a67e&X-Amz-SignedHeaders=host&response-content-disposition=filename%20%3D%22Untitled.png%22&x-id=GetObject)

## Server

當接收client的Setup時，開啟三個thread (分別傳送或接受RTP, RTSP, RTCP)，並進入PAUSE mode，等待收到client端的PLAY指令時，才開始傳送影片，在傳送影片時，除了監聽RTSP指令以決定PLAY,PAUSE,TEARDOWN動作外。亦會監聽RTCP指令，以控制傳送速度、影像品質，以避免網路阻塞 。

Congestion level計算公式如下：

由 RTCP 指令中的 fraction lost，計算當前的 congestion level，並依照 congestion level(0~5)，壓縮每張frame的解析度、控制傳送速度，以避免網路阻塞 。

![server.jpeg](https://s3.us-west-2.amazonaws.com/secure.notion-static.com/518cede5-954c-4ef2-bde8-aa51f3a3fb67/Untitled.png?X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Content-Sha256=UNSIGNED-PAYLOAD&X-Amz-Credential=AKIAT73L2G45EIPT3X45%2F20220124%2Fus-west-2%2Fs3%2Faws4_request&X-Amz-Date=20220124T134330Z&X-Amz-Expires=86400&X-Amz-Signature=1f515c04cb38200a94365934b2e781d0582fbc2b4031b92f25a7955c88c95325&X-Amz-SignedHeaders=host&response-content-disposition=filename%20%3D%22Untitled.png%22&x-id=GetObject)

### `CongestionController`

負責根據 congestion level 變更傳送速度

### `ImageTranslator`

根據 congestion level 壓縮傳送影片

### Lost Packet Simulation

可以利用 `-l` 的 argument 去決定 loss 的機率，模擬封包遺失的狀況

## Client

使用方式：在點選setup按鈕後，即可完成RTP, RTSP, RTCP的connection。可透過PLAY, PAUSE, TEARDOWN按鈕完成播放、暫停、關閉等動作。另外會計算當前的packet loss，並透過RTCP封包告訴Server端當前的傳送品質，以利Server得知網路壅塞情況。

Packet lost計算：

每次接收 RTP packet  時，Client 會紀錄預期收到的下個封包 (excepted sequence number) ，並透過核對 RTP 封包 sequence number 計算累積的丟失封包數量 (cumulative_lost)，並以公式fraction_lost = # packet lost / total packet 計算出fraction_lost，裝入RTCP封包傳送給Server。Server將以此指標計算網路壅塞程度

實作如下圖：

![Untitled](https://s3.us-west-2.amazonaws.com/secure.notion-static.com/3079b446-33d1-4b81-8031-697357481fca/Untitled.png?X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Content-Sha256=UNSIGNED-PAYLOAD&X-Amz-Credential=AKIAT73L2G45EIPT3X45%2F20220124%2Fus-west-2%2Fs3%2Faws4_request&X-Amz-Date=20220124T134611Z&X-Amz-Expires=86400&X-Amz-Signature=5359884904e9e59cbbb549d6f88e9b44c2180c05fd597fdae657243ed6b371e1&X-Amz-SignedHeaders=host&response-content-disposition=filename%20%3D%22Untitled.png%22&x-id=GetObject)

### Object Detection

Ref: [https://github.com/EdjeElectronics/TensorFlow-Lite-Object-Detection-on-Android-and-Raspberry-Pi/blob/master/Raspberry_Pi_Guide.md](https://github.com/EdjeElectronics/TensorFlow-Lite-Object-Detection-on-Android-and-Raspberry-Pi/blob/master/Raspberry_Pi_Guide.md)

將 client 收到的每張 frame 通過一個 pretrain 的 tflite object detection model，並將結果以方框直接標示於畫面中，並顯示出判斷信心。由於該 model 原本是為 raspberry pi 所設計，不需太多的計算資源，因此 inference 並不會對 fps 產生影響。

### GUI

- 使用PyQt5套件來產生GUI畫面。
- 是用四個 QPushButton 來產生 setup, play, pause, breakdown，四個按鈕，並依序加入QVBoxLayout來產生左邊的按鈕列。
- 畫面則是採用 qlabel 來產生，並使用 pyqtSignal 來更新 frame 以播出影片。
- 最右邊的 layout 則是 使用 qlabel 來印出各種統計資料，並且再每更新固定張數的 frame 後更新數據，以增加可讀性。
- 最後將以上三個部分依序加入 QHBoxLayout 來產生最終的畫面。

![4AFD893F-E697-4C53-8636-6E2051A7C8FE.png](https://s3.us-west-2.amazonaws.com/secure.notion-static.com/4f642280-2d15-473f-9a54-0053ac7e8fee/4AFD893F-E697-4C53-8636-6E2051A7C8FE.png?X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Content-Sha256=UNSIGNED-PAYLOAD&X-Amz-Credential=AKIAT73L2G45EIPT3X45%2F20220124%2Fus-west-2%2Fs3%2Faws4_request&X-Amz-Date=20220124T134625Z&X-Amz-Expires=86400&X-Amz-Signature=31bf457e057b84433cf57751cdf29f609b75b1d7730f9165db918409358b88cf&X-Amz-SignedHeaders=host&response-content-disposition=filename%20%3D%224AFD893F-E697-4C53-8636-6E2051A7C8FE.png%22&x-id=GetObject)

## 執行方式

### **Installation**

Clone the repository with `https://github.com/Fiona1121/ICN-final-project.git`.

Having python>=3.6 installed, create a virtual environment by running `python -m venv venv` inside the cloned folder.

Activate the virtual environment (`source venv/bin/activate` on Linux, `.\venv\Scripts\activate` on Windows).

Install the requirements with `python -m pip install -r requirements.txt`.

### **Usage**

Server should be run first with

`python main_server.py`

To specify server ip, port, or session ID

```bash
$ python main_server.py -h
usage: main_server.py [-h] [-i IPADDRESS] [-p PORT] [-s SESSIONID] [-l PROBLOST]

optional arguments:
 -h, --help            show this help message and exit
 -i IPADDRESS, --IPADDRESS IPADDRESS
                       The RTSP server IP address
 -p PORT, --PORT PORT  The port number
 -s SESSIONID, --SESSIONID SESSIONID
                       Session IDServer session ID
 -l PROBLOST           Probability of rtp packet loss
```

Client can be run with

```bash
python main_client.py <filename> <host> <server_port> <client_port>
```
