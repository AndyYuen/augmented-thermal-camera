import cv2
import numpy as np
import time
import os
import math
import threading
from flask import Flask, render_template, request, Response
from flask_sock import Sock
from collections import deque, namedtuple
from ThermalImage import Tlite

app = Flask(__name__)

sock = Sock(app)
wsQueue = deque()

# setup thermal image parmeters
WIDTH = 800
HEIGHT = 600
# use the offsets to move the centre of the thermal image to align with the normal image
# x_offset = -40
# y_offset = 0

# setup thread-safe queue to pass image from t-lite thread to main thread
# and introducing condition variable to do blocked wait
tliteQueue = deque()
tliteCond = threading.Condition()

# data to be saved in tliteQueue
TliteData = namedtuple("TliteData", "image temperatures")

# setup thread-safe queue to pass image from RTSP thread to main thread
rtspQueue = deque()
rtspCond = threading.Condition()


# thread function to get t-lite heat image
# this thread is used to speed up download of heat image from t-lite
def tlite_thread(size, cond):
    global WIDTH, HEIGHT, t_lite_url, tliteQueue, cmap_dictionary, x_offset, y_offset

    # Crete object to call T-Lite REST Service
    thermal = Tlite(t_lite_url)
    imgCount = 0
    reportCount = 20
    prev_time = time.time()
    while True:

        # get thermal data
        thermal.getThermalData()

        # if display == "thermal" or display == "both":
        thermalImg = crop_center(thermal.convertToImage(size, 
            cmap_dictionary.get(colormap)), WIDTH, HEIGHT, x_offset, y_offset)
        # only put it in the tliteQueue if it is needed
        # tliteQueue.clear()
        with cond:
            tliteQueue.append(TliteData(thermalImg, thermal.getTemperatureSummary()))
            # remove old image
            if len(tliteQueue) > 2:
                tliteQueue.popleft()
            # else:
            #     tliteQueue.clear()
            cond.notify()

        imgCount += 1
        if imgCount >= reportCount:
            interval = time.time() - prev_time
            fps = imgCount / interval
            print("tlite fps: {:.1f}".format(fps))
            imgCount = 0
            prev_time = time.time()


# thread function to get RTSP stream
# this thread is used to speed up reading RTSP stream
def rtsp_thread(url, cond):
    # set up normal camera video stream 
    vcap = cv2.VideoCapture(rtsp_url)
    vcap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
    # fps = vcap.get(cv2.CAP_PROP_FPS)
    # print("FPS: {}".format(fps))
    # frameCount = 0
    # skipCount = 1

    while True:

        success, image = vcap.read()
        if not success or image is None:
            print("Failed to read frame or frame is None.")
            break

        else:
            with cond:
                rtspQueue.append(image)
                if len(rtspQueue) > 2:
                    rtspQueue.popleft()
                cond.notify()
            
        # frameCount += 1

# calculate image scaling factor based on FOVs
def calcImageScale(normalFOC, thermalFOV):
    imageScale = math.tan(math.radians(normalFOC / 2.))/math.tan(math.radians(thermalFOV / 2.))
    print("ImageScale: {}".format(imageScale))
    return imageScale

# crop the center region of an image with size width/height cripx/cropy
def crop_center(img, cropx, cropy, x_offset, y_offset):
    y,x,_ = img.shape
    startx = x // 2-(cropx // 2) + x_offset
    starty = y // 2-(cropy // 2) + y_offset
    return img[starty: starty+cropy, startx: startx+cropx, :]

# video generator. Each client has its own video generator.
def generateFrames(ws): 

    # variable used in calaculating fps
    # prev_time = time.time()
    # frCount = 0
    # fps = str(0)

    # setup camera parameters 65:90
    NORMAL_FOV = 70
    THERMAL_FOC = 90
    imageScale = calcImageScale(NORMAL_FOV, THERMAL_FOC)

    global tlite_thread, tliteCond, rtsp_thread, rtsp_url, rtspCond

    # create thread to use REST API to get tlite temperature image
    tThread = threading.Thread(target=tlite_thread, daemon=True, 
        args=((int(WIDTH / imageScale), int(HEIGHT / imageScale)), tliteCond,))
    tThread.start()

    # create thread to get frames from the RTSP camera
    rThread = threading.Thread(target=rtsp_thread, daemon=True, 
        args=(rtsp_url, rtspCond,))
    rThread.start()

    # # set up normal camera video stream 
    # vcap = cv2.VideoCapture(rtsp_url)
    # vcap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
    # fps = vcap.get(cv2.CAP_PROP_FPS)
    # print("FPS: {}".format(fps))
    #skipCount = int(fps / float(target_fps))
    # skipCount = 2
    # frameCount = 0

    # set up image variables
    resultImg = None
    thermalImg = None
    normalImg = None
    image = None
    while True:

        with rtspCond:
            rtspCond.wait()
            image = rtspQueue.pop()
        # frameId = int(round(vcap.get(1)))
        # frameCount += 1
        # if skipCount > 1 and frameCount % skipCount == 0:

        if display == "normal" or display == "both":

            #image = np.rot90(image)

            grayscale = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            grayscaleUint8 = np.uint8(np.absolute(grayscale))

            # looks like blur gives a better result
            blur = cv2.GaussianBlur(grayscale, (3, 3), 0)

            # convert to uint8 for adaptive thresholding
            blurUint8 = np.uint8(np.absolute(blur))

            normalImg = image
            if algorithm == "none":
                # Perform Canny edge detection 
                # normalImg = cv2.Canny(blurUint8, canny_low, canny_low * canny_ratio)
                # normalImg = cv2.bitwise_not(normalImg)

                # testing just grey scale
                normalImg = grayscaleUint8

                # testing adaptive OTSU algorithm
                # ret, normalImg = cv2.threshold(blur, 127, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            elif algorithm == "gauss":
                # Use Gaussian
                normalImg = cv2.adaptiveThreshold(blurUint8, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2)
            elif algorithm == "mean":
                # Use mean
                normalImg = cv2.adaptiveThreshold(blurUint8, 255, cv2.ADAPTIVE_THRESH_MEAN_C, cv2.THRESH_BINARY, 11, 2)


            if ws is None:
                print("ws not set in generateFrames.")
                break
            # else:
            #     getThermalFlag = False      


            # display FPS near top right-hand corner
            #cv2.putText(image, fps, (image.shape[1] - 120, 70), 
            #    cv2.FONT_HERSHEY_SIMPLEX, 3, (100, 255, 0), 3, cv2.LINE_AA)

        # get data from thermal camera using REST API
        if display == "thermal" or display == "both":
            # if getThermalFlag or thermalImg is None:
            data = None
            with tliteCond:
                tliteCond.wait()
                data = tliteQueue.pop()
                thermalImg = data.image
                
            try:
                # send array of temperature to client
                ws.send(data.temperatures)

            except:
                break

                
        # decide on what to dsplay
        if display == "thermal":
            # display thermal camera image only
            if thermalImg is None:
                print("thermal: thermalImg is None.")
                continue
            resultImg = thermalImg
        elif display == "normal":
            # display normal camera edge image
            if normalImg is None:
                print("normal: normalImg is None.")
                continue
            resultImg = normalImg
        elif display == "both":
            # overlap the thermal image with the normal edge image
            if normalImg is None or thermalImg is None:
                if normalImg is None:
                    print("both: normalImg is None.")
                elif thermalImg is None:
                    print("both: thermalImg is None.")
                else:
                    print("both: normalImg is None and thermalImg is None.")
                continue
            # convert normalImg to the same type as thermalImg ie, from grayscale to colour
            img2 = cv2.merge((normalImg, normalImg, normalImg))

            # overlay images from both cameras
            global alpha
            beta = (1.0 - alpha)
            resultImg = cv2.addWeighted(thermalImg, alpha, img2, beta, 0.0)

        # convert image to jpeg and let client display jpeg images quickly to simulate a video
        ret, buffer = cv2.imencode('.jpg', resultImg)
        frame = buffer.tobytes()

        thermalImg = None
        normalImg = None

        yield (b'--frame\r\n'
            b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')  # concat frame one by one and show result

# Stream video to the client
@app.route('/video')
def video():

    ws = None

    for x in range(3):
        if len(wsQueue) == 0:
            print("Waiting to get ws.")
            time.sleep(2)

    if len(wsQueue) == 0:
        # failed to get client websocket, no video will be streamed
        print("wsQueue empty.")
        return "No websocket for event notification."
    else:
        ws = wsQueue.popleft()
        print ("ws set.")

    # invoke video generator to get frames
    return Response(generateFrames(ws), mimetype='multipart/x-mixed-replace; boundary=frame')

# render home page
@app.route('/')
def renderPage():
    return render_template('index.html')


# let client register its websocket for sending commands and
# receiving events
# Note: websocket registration is mandatary for video streaming to work with index.html
@sock.route('/events')
def events(ws):
    print("Reached events route.")

    wsQueue.append(ws)
    while True:
        data = ws.receive()
        print("Recieved: {}".format(data))
        category = cmd_dictionary.get(data)
        # process commands from UI
        if category is not None:
            global algorithm, display, colormap, x_offset, y_offset
            if category == "algorithm":
                algorithm = data
            elif category == "display":
                display = data
            elif category == "colormap":
                colormap = data
            elif category == "alignment":
                if data == "left":
                    x_offset += 5
                elif data == "right":
                    x_offset += -5
                elif data == "up":
                    y_offset += 5
                elif data == "down":
                    y_offset += -5
                else:
                    x_offset = 0
                    y_offset = 0

                print("x_offset={}, y_offset={}".format(x_offset, y_offset))
    #     if data == 'stop':
    #         break


if __name__ == '__main__':
    # retrieve env variables
    rtsp_url = os.environ['RTSP_URL']
    t_lite_url = os.environ['T_LITE_URL']

    x_offset = int(os.getenv('X_OFFSET', default=0))
    y_offset = int(os.getenv('Y_OFFSET', default=0))
    alpha = float(os.getenv('ALPHA', default=0.6))

    # command dictionary to get command type
    cmd_dictionary = {
        "canny" : "algorithm",
        "gauss" : "algorithm",
        "mean"  : "algorithm",
        "none"  : "algorithm",
        "thermal" : "display",
        "normal"  : "display",
        "both"  : "display",
        "jet"   : "colormap",
        "inferno" : "colormap",
        "turbo" : "colormap",
        "left" : "alignment",
        "reset" : "alignment",
        "up" : "alignment",
        "down" : "alignment",
        "right" : "alignment"
    }

    # colormap dictionary to get CV colormap name
    cmap_dictionary = {
        "jet" : cv2.COLORMAP_JET,
        "inferno" : cv2.COLORMAP_INFERNO,
        "turbo" : cv2.COLORMAP_TURBO
    }

    # initial states align with the defaults in the index.html file
    algorithm = "none"
    display = "thermal"
    colormap = "jet"

    print("* {}: {}".format('rtsp_url', rtsp_url))
    print("* {}: {}".format('t_lite_url', t_lite_url))
    print("* {}: {}".format('x_offset', x_offset))
    print("* {}: {}".format('y_offset', y_offset))
    print("* {}: {}".format('aphha', alpha))

    app.run(host="0.0.0.0", port=4000)
