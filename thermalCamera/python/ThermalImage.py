import requests
import json
import cv2
import numpy as np

class Tlite:

    def __init__(self, url):
        self.url = url
        self.json = None

        # it appears that without using a user-agent header causes frequent pauses and
        # and 'Remote end closed connection without response error' after a while
        # https://stackoverflow.com/questions/50597923/unable-to-requests-get-a-website-remote-end-closed-connection-without-respon
        self.headers =  {"Content-Type":"application/json", "User-Agent":"Mozilla/5.0"}

    def getThermalData(self):
        try:
            response = requests.get(self.url, headers=self.headers)
            self.json = response.json()
        except requests.exceptions.RequestException as e:
            print("GET request error.")
            raise SystemExit(e)


    def getTemperatureSummary(self):
        return "[ {:.1f}, {:.1f}, {:.1f}, {:.1f} ]".format(self.json['average'], 
            self.json['center'], self.json['lowest'], 
            self.json['highest'])


    def convertToImage(self, size, colormap):

        imageArray = np.array(self.json['frame'], dtype=np.float32)
        image = imageArray.reshape(24,32,1)

        # Convert source image to unsigned 8 bit integer Numpy array
        image = image - image.min() # Now between 0 and 8674
        image = image / image.max() * 255
        imuint8 = image.astype(np.uint8)
        imBig = cv2.resize(imuint8, size, interpolation=cv2.INTER_LINEAR)
        imC = cv2.applyColorMap(imBig, colormap)

        return imC

if __name__ == '__main__':
    # Execute when the module is not initialized from an import statement.
    # this is a test of this class
    thermal = Tlite("http://192.168.1.145/json")
    thermal.getThermalData()
    image = thermal.convertToImage((800, 600), cv2.COLORMAP_INFERNO)
    cv2.imshow("myWindow", image)

    # closing all open windows 
    cv2.waitKey(10000)
    cv2.destroyAllWindows() 

