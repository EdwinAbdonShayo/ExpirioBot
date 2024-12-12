# Importing Dependencies
import pygame,sys
from pygame.locals import *
import numpy as np
from keras.models import load_model
import cv2

# Dimensions of Display Window
width = 720
height = 540

# Margin & colors
BOUNDARY = 5
white = (255,255,255)
black = (0,0,0)
red = (255,0,0)

IMAGESAVE = False

MODEL = load_model("model.h5")

lables = {0:"Zero", 1:"One", 2:"Two", 3:"Three", 4:"Four", 5:"Five", 6:"Six", 7:"Seven", 8:"Eight", 9:"Nine"}

# Initializing pygame
pygame.init()

FONT = pygame.font.SysFont("consolas", 20, bold=True)
Display = pygame.display.set_mode((width,height))

pygame.display.set_caption("Black Board")

iswriting = False
x_cord = []
y_cord = []

PREDICT=True

while True:
    for event in pygame.event.get():
        if event.type==QUIT:
            pygame.quit()
            sys.exit()

        if event.type==MOUSEMOTION and iswriting:
            x,y = event.pos
            pygame.draw.circle(Display,white,(x,y),3,0)
            x_cord.append(x)
            y_cord.append(y)

        if event.type == MOUSEBUTTONDOWN:
            iswriting = True

        if event.type == MOUSEBUTTONUP:
            iswriting = False
            x_cord = sorted(x_cord)
            y_cord = sorted(y_cord)
            rect_min_x,rect_max_x = max(x_cord[0]-BOUNDARY,0),min(width,x_cord[-1]+BOUNDARY)
            rect_min_y,rect_max_y = max(y_cord[0]-BOUNDARY,0),min(width,y_cord[-1]+BOUNDARY)   

            x_cord=[]
            y_cord=[]

            img_arr = np.array(pygame.PixelArray(Display))[rect_min_x:rect_max_x,rect_min_y:rect_max_y].T.astype(np.float32)

            if PREDICT:
                image = cv2.resize(img_arr,(28,28))
                image = np.pad(image,(10,10),'constant',constant_values=0)
                image = cv2.resize(image,(28,28))/255

                IMAGESAVE=True

                digit = np.argmax(MODEL.predict(image.reshape(1,28,28,1)))
                # if IMAGESAVE:
                #     cv2.imwrite('image_{}.png'.format(digit),image)
                
                label = str(lables[digit])

                text = FONT.render(label,True,(255,255,0))
                RectObj = pygame.draw.rect(Display,red, pygame.Rect(rect_min_x, rect_min_y, rect_max_x-rect_min_x,rect_max_y-rect_min_y),2)

                Display.blit(text, (rect_min_x,rect_min_y-18))
            
        if event.type==pygame.KEYDOWN:
            if event.key== pygame.K_BACKSPACE:
                Display.fill(black)

    pygame.display.update()