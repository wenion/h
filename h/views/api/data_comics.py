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
globalheight = 230
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
def createImageNavigate(url,title,processID):
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
    return "data:image/jpg;base64,"+resEncode.decode("utf-8")
    
# This fuction create the event images
def createBasicImage(event,text,typeSize,processID):
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
        imgText=positionTextEvent(text,globalheight-60,width-posRecShort)
        y_offset=50
        x_offset=125#Cambia
        img[y_offset:y_offset+imgText.shape[0], x_offset:x_offset+imgText.shape[1]] = imgText
    # Displaying the image  
    img= addIcon(img,event)
    retval, buffer = cv2.imencode('.jpg', img)
    resEncode = base64.b64encode(buffer)#Convert to base64
    return "data:image/jpg;base64,"+resEncode.decode("utf-8")
# This fuction create the image to the data comics summary
def createCircule(processName,title,flagArrow):
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
    return "data:image/jpg;base64,"+resEncode.decode("utf-8")
###-----------Auxiliar function --------------
# This function add and image(icon) depending on the event
def addIcon(imgLarge,event):
    if event.lower()=="click":
        imgBase64=b'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'
    elif event.lower()=="type":
        imgBase64=b'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'
    elif event.lower()=="scroll":
        imgBase64=b'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'
    elif event.lower()=="annotate":
        imgBase64=b'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'
    elif event.lower()=="select":
        imgBase64=b'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'
    im_arr= np.frombuffer(base64.b64decode(imgBase64), dtype=np.uint8)
    imgSmall = cv2.imdecode(im_arr, flags=cv2.IMREAD_COLOR)

    y_offset=50
    x_offset=10
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
# This function center the text vertical align in the events
def positionTextEvent(label,heigth,width):
    img = np.zeros((heigth,width-8,3), np.uint8)#Cambiar 350
    img.fill(255)

    tam=len(label)
    cont=0
    if tam>=250:
        tam=250
    heigthtext=tam/48
    if heigthtext>=5:    
        heigthtext=4
    pos=50
    lenText=28
    auxCont=0
    flagFinish=False
    for x in range(0,tam,lenText):
        x=x-auxCont
        if (lenText+x)>=tam: text=label[x:tam]
        else:text= label[x:lenText+x]
        #if text[len(text)]!=''
        if cont>=140:
            text=text[:len(text)]+"..."
            print("CONT")
            flagFinish=True
        elif len(text)>=lenText: 
            pos=text.rfind(" ")
            text=text[:pos]
            pos=pos+1# for empty space
            auxCont=auxCont+(lenText-pos)  
        cv2.putText(img, text, (8,90+cont-(int(heigthtext)*18)), font, fontDescription, colorOrange, thickness,cv2.LINE_AA)
        cont= cont +20
        if flagFinish: break
    #cv2.imshow("Event", img)
    #k = cv2.waitKey(0)
    return img
# This function add the an arrow to the circule image 
def addArrow(imgLarge):
    imgBase64= b'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'
    im_arr= np.frombuffer(base64.b64decode(imgBase64), dtype=np.uint8)
    imgSmall = cv2.imdecode(im_arr, flags=cv2.IMREAD_COLOR)
    y_offset=70
    x_offset=201
    imgLarge[y_offset:y_offset+imgSmall.shape[0], x_offset:x_offset+imgSmall.shape[1]] = imgSmall

    return imgLarge
###-----------Auxiliar function --------------

def create_images_DC(data):
    for process in data['KM_Process']:
        code_process=process['code']
        name_process=process['name']
        process['image']=createCircule(name_process,process['title'],True)
        for event in process['steps']:
            if event['type']=='Navigation':
                event['image']=createImageNavigate(event['url'],event['title'],code_process)
            elif event['type']=='Click':
                event['image']=createBasicImage(event['type'],event['description'],1,code_process)
            elif event['type']=='Scroll':
                event['image']=createBasicImage(event['type'],"",1,code_process)
            elif event['type']=='Select':
                event['image']=createBasicImage(event['type'],event['description'],1,code_process)
            elif event['type']=='Type':
                event['image']=createBasicImage(event['type'],event['description'],1,code_process)
            elif event['type']=='Annotate':
                event['image']=createBasicImage(event['type'],event['description'],1,code_process)
            elif event['type']=='Uploaded':
                event['image']=createBasicImage(event['type'],event['description'],1,code_process)
    return data
