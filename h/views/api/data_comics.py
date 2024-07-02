import cv2
import numpy as np
from h.security import Permission
from h.views.api.config import api_config
import json
import base64
from h.views.api.user_manipultations import expert_replay
from h.views.api.data_comics_process import  data_commics_process

#Global variables
globalWidth = 800
globalheight = 250
heightNavigate= 115
font                   = cv2.FONT_HERSHEY_DUPLEX
fontTitle             = 0.7 #font size
fontDescription       = 0.5 #font size
colorOrange              = (0,165,255)
thickness              = 1 
thicknessRec = 2
colorBlack = (1, 1, 1)
start_point = (5, 5) 

#This function create the navigate images
def createImageNavigate(url,title,processID,position,cont):
    img = np.zeros((heightNavigate,globalWidth,3), np.uint8)
    img.fill(255)

    #text= "Navigate to: " +str(url)+ "\n Title: "+str(title)
    cv2.rectangle(img, start_point, (globalWidth-5, heightNavigate-3), colorBlack, thicknessRec,cv2.LINE_AA)# Rec Big
    
    if len("Title: "+str(title))< 61:
        cv2.putText(img,"Navigate to: ", (int(centerTextHorizontal("Navigate to",globalWidth,fontTitle)),50), font, fontTitle,colorBlack,thickness,cv2.LINE_AA)
        cv2.putText(img,"Title: "+str(title), (int(centerTextHorizontal("Title: "+str(title),globalWidth,fontTitle)),80), font, fontTitle,colorOrange,thickness,cv2.LINE_AA)
    else : 
        cv2.putText(img,"Navigate to: ", (int(centerTextHorizontal("Navigate to",globalWidth,fontTitle)),35), font, fontTitle,colorBlack,thickness,cv2.LINE_AA)
        imgText=centerTextVertical("Title: "+str(title),globalWidth,fontTitle)
        y_offset=50
        x_offset=20
        img[y_offset:y_offset+imgText.shape[0], x_offset:x_offset+imgText.shape[1]] = imgText
    
    retval, buffer = cv2.imencode('.jpg', img)
    resEncode = base64.b64encode(buffer)#Convert to base64
    return str(resEncode)
    
# This fuction create the event images
def createBasicImage(event,text,typeSize,processID,position,cont):
    width=int(globalWidth/2)
    posText=200
    posRecShort=125
    img = np.zeros((globalheight,width,3), np.uint8)
    img.fill(255) # or img[:] = 255

    # represents the bottom right corner of rectangle 
    end_point = (width-5, globalheight-5) 
    cv2.rectangle(img, start_point, end_point, colorBlack, thicknessRec,cv2.LINE_AA)# Rec Big
    cv2.rectangle(img, (posRecShort, 5), (width-5,45), colorBlack, thicknessRec,cv2.LINE_AA)
    #cv2.putText(img, event, (width-posText,35), font, fontScale, colorBlack, thickness, cv2.LINE_AA)
    print(str(int((width-posRecShort)/2)))
    cv2.putText(img, event, (int(centerTextHorizontal(event,width,fontTitle))+int(posRecShort/2),35), font, fontTitle, colorBlack, thickness, cv2.LINE_AA)
    if len(text)<=20:
        cv2.putText(img, text,(int(centerTextHorizontal(text,width,fontTitle))+int(posRecShort/2),int(globalheight/2)+10), font, fontTitle, colorOrange, thickness,cv2.LINE_AA)
    else:
        imgText=centerTextVertical(text,globalheight-60,width-posRecShort)
        y_offset=50
        x_offset=125#Cambia
        img[y_offset:y_offset+imgText.shape[0], x_offset:x_offset+imgText.shape[1]] = imgText
    # Displaying the image  
    img= addIcon(img,event)
    retval, buffer = cv2.imencode('.jpg', img)
    resEncode = base64.b64encode(buffer)#Convert to base64
    return str(resEncode)
# This fuction create the image to the data comics summary
def createCircule(processName,title,position,flagArrow):
    widthCircule=201
    radio=100
    heightCircule=270
    if flagArrow:
        img = np.zeros((heightCircule,widthCircule+50,3), np.uint8)
        img.fill(255)
    else:    
        img = np.zeros((heightCircule,widthCircule,3), np.uint8)
        img.fill(255)
    cv2.circle(img, (radio, radio), radio, colorBlack, 2,cv2.LINE_AA)
    if len(processName)<18:
        cv2.putText(img, processName, (int(centerTextHorizontal(processName,radio*2,fontTitle)),108), font, fontTitle, colorOrange, thickness,cv2.LINE_AA)
    else:
        imgText=positionTextCircule(processName,45, widthCircule,23,12)
        y_offset=85
        x_offset=10
        img[y_offset:y_offset+imgText.shape[0], x_offset:x_offset+imgText.shape[1]] = imgText   
    if len(title)<=15:
        cv2.putText(img, title, (int(centerTextHorizontal(title,radio*2,fontTitle)),(radio*2)+30), font, fontTitle, colorOrange, thickness,cv2.LINE_AA)
    else: 
        imgText=positionTextCircule(title,50, widthCircule,30,16)
        y_offset=(radio*2)+10
        x_offset=10
        img[y_offset:y_offset+imgText.shape[0], x_offset:x_offset+imgText.shape[1]] = imgText
    img=addArrow(img)
    retval, buffer = cv2.imencode('.jpg', img)
    resEncode = base64.b64encode(buffer) #Convert to base64
    return str(resEncode)
###-----------Auxiliar function --------------
# This function add and image(icon) depending on the event
def addIcon(imgLarge,event):
    path="icons//"+event.lower()+".png"
    imgSmall = cv2.imread(path)

    y_offset=50
    x_offset=10#Cambia
    imgLarge[y_offset:y_offset+imgSmall.shape[0], x_offset:x_offset+imgSmall.shape[1]] = imgSmall

    return imgLarge
# This function center the text horizontal align
def centerTextHorizontal(text, width, font_Size):
    if font_Size==fontTitle:
        (label_width, label_height), baseline = cv2.getTextSize(text, font, font_Size, thickness)
        textX = int((width - (label_width))/2)# get coords based on boundary
        return textX
    elif font_Size==fontDescription:
        (label_width, label_height), baseline = cv2.getTextSize(text, font, font_Size, thickness)
        textX = int((width - (label_width))/2)
        return textX    
# This function center the text horizontal vertical align
def centerTextVertical(label,font_size, width):
    maxCharacter=122
    if len(label)> maxCharacter: label=label[:maxCharacter-3]+"..."
    img = np.zeros((60,globalWidth-40,3), np.uint8)#Cambiar 350
    img.fill(255)

    tam=len(label)
    lenText=61
    pos=auxCont=cont=0
    for x in range(0,tam,lenText):
        x=x-auxCont
        if (lenText+x)>=tam: text=label[x:tam]
        else:text= label[x:lenText+x]
        if len(text)>=lenText: 
            pos=text.rfind(" ")
            text=text[:pos]
            pos=pos+1# for empty space
            auxCont=auxCont+(lenText-pos)
        # get boundary of this text
        (label_width, label_height), baseline = cv2.getTextSize(text, font, fontTitle, thickness)
        # get coords based on boundary
        textX = int((img.shape[1] - (label_width))/2)
        # add text centered on image
        cv2.putText(img, text, (textX, (cont*25)+15), font, fontTitle, colorOrange, thickness,cv2.LINE_AA)
        cont= cont +1
    #cv2.imshow("Event", img)
    #k = cv2.waitKey(0)
    return img 
# This function position the text in the circule image
def positionTextCircule(label,heigth, width,maxCharacter,lenText):
    if len(label)> maxCharacter: label=label[:maxCharacter-3]+"..."
    img = np.zeros((heigth,width-20,3), np.uint8)#Cambiar 350
    img.fill(255)

    tam=len(label)
    pos=auxCont=cont=0
    for x in range(0,tam,lenText):
        x=x-auxCont
        if (lenText+x)>=tam: text=label[x:tam]
        else:text= label[x:lenText+x]
        if len(text)>=lenText: 
            pos=text.rfind(" ")
            text=text[:pos]
            pos=pos+1# for empty space
            auxCont=auxCont+(lenText-pos)
        print(text)
        # get boundary of this text
        (label_width, label_height), baseline = cv2.getTextSize(text, font, fontTitle, thickness)
        # get coords based on boundary
        textX = int((img.shape[1] - (label_width))/2)
        # add text centered on image
        cv2.putText(img, text, (textX, (cont*25)+15), font, fontTitle, colorOrange, thickness,cv2.LINE_AA)
        cont= cont +1
    #cv2.imshow("Event", img)
    #k = cv2.waitKey(0)
    return img
# This function add the an arrow to the circule image 
def addArrow(imgLarge):
    path="icons//arrow.png"
    imgSmall = cv2.imread(path)

    y_offset=70
    x_offset=201
    imgLarge[y_offset:y_offset+imgSmall.shape[0], x_offset:x_offset+imgSmall.shape[1]] = imgSmall

    return imgLarge
###-----------Auxiliar function --------------

#
def create_images_DC(data):
    print("CREATE IMAGE DC")
    posProcess=1
    for process in data['KM_Process']:
        contImages=1
        code_process=process['name'].split(" ")[0]
        name_process=process['name'].split(" ")[1]
        process['image']=createCircule(name_process,process['title'],posProcess,True)
        for event in process['steps']:
            if event['type']=='Navigation':
                event['image']=createImageNavigate(event['url'],event['title'],code_process,posProcess,contImages)
            elif event['type']=='Click':
                event['image']=createBasicImage(event['type'],event['description'],1,code_process,posProcess,contImages)
            elif event['type']=='Scroll':
                event['image']=createBasicImage(event['type'],"",1,code_process,posProcess,contImages)
            elif event['type']=='Select':
                event['image']=createBasicImage(event['type'],event['description'],1,code_process,posProcess,contImages)
            elif event['type']=='Type':
                event['image']=createBasicImage(event['type'],event['description'],1,code_process,posProcess,contImages)
            elif event['type']=='Annotate':
                event['image']=createBasicImage(event['type'],event['description'],1,code_process,posProcess,contImages)
            elif event['type']=='Uploaded':
                event['image']=createBasicImage(event['type'],event['description'],1,code_process,posProcess,contImages)
            contImages=contImages+1
        posProcess=posProcess+1