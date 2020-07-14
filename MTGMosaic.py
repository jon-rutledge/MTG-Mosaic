
from PIL import ImageStat
from PIL import ImageColor
from PIL import Image, ImageDraw
from io import BytesIO
import sqlite3
import math
import base64
import traceback
import numpy as np
import os
import time
'''


TO DO:
1. Add logic for border slice for cards older than 8th Edition
2. Remove cards that do not fit normal picture convention, right now playtest cards seem to be the only problem
3. look into optimization, currently takes a long time.

'''


def getImageAvgHSV(imageObject):
    '''
    returns the average HSV values in an array for a supplied image object.
    '''
    im = imageObject
    im = im.convert('HSV')
    im_stats = ImageStat.Stat(im)
    im_stats.mean[0] = im_stats.mean[0]/255*360
    im_stats.mean[1] = im_stats.mean[1]/255*100
    im_stats.mean[2] = im_stats.mean[2]/255*100

    hsv_mean = [round(x) for x in im_stats.mean]

    return tuple(hsv_mean)

def compareAvgHSV_OLD(PrimaryHSV, CompareHSV):
    '''
    OLD METHOD for HSV comparisons.  
    Still here for demonstrating why it is inferior
    Function to compare 2 sets of HSV to compare.

    takes 2 arrays of HSV values
    '''

    h_comp = abs(PrimaryHSV[0]/360-CompareHSV[0]/360)
    s_comp = abs(PrimaryHSV[1]/100-CompareHSV[1]/100)
    v_comp = abs(PrimaryHSV[2]/100-CompareHSV[2]/100)

    #print([r_comp,g_comp, b_comp])
    #print(max([r_comp,g_comp, b_comp]))

    return max([h_comp,s_comp, v_comp])

def compareHSV(PrimaryHSV, CompareHSV):
    '''
    Function to compare 2 sets of RGB to compare.

    uses 3d vector to compare rather than previous method.

    '''

    h_comp = abs(PrimaryHSV[0]/360-CompareHSV[0]/360)
    s_comp = abs(PrimaryHSV[1]/100-CompareHSV[1]/100)
    v_comp = abs(PrimaryHSV[2]/100-CompareHSV[2]/100)

    vector = math.sqrt(h_comp**2 + s_comp**2 + v_comp**2)

    #print([r_comp,g_comp, b_comp])
    #print(max([r_comp,g_comp, b_comp]))

    return vector

def cropArtModern(image):
    '''
    function to crop art from modern card frame.  This is from 8ED onward.
    dimensions are hardcoded based on some trial and error testing.
    '''
    width, height = image.size
    (left, upper, right, lower) = (width*.092, height*.13, width*.908, height*.55)
    im_crop = image.crop((left, upper, right, lower))
    return im_crop

def ResizeImageForPixel(image, pix_width, pix_height):
    '''
    For images that will be used as the mosaic tiles, we neeed
    to correctly adjust their size in order to get a better end result
    average color.  

    We also need to make sure we crop/resize in a way that does not distort.

    rescaled version should always be smaller
    '''

    #determine portion of image to be used for pixel
    im = image
    width, height = im.size

    max_dim = min(width,height)
    #print(max_dim)

    if width >= height:
        left = round((width - max_dim) / 2)
        top = round((height - max_dim) / 2)
        right = round(max_dim + left)
        bottom = round(max_dim + top)
    
    else:
        left = round((width - max_dim) / 2)
        top = round((height - max_dim) / 10)
        right = round(max_dim + left)
        bottom = round(max_dim + top)

    new_dim = (left, top, right, bottom)

    im = im.crop(new_dim)
    im = im.resize((pix_width,pix_height))
    #im.show()
    #print(new_dim)

    return im



def findBestTileMTG(targetColor, DBconnection, pix_width, pix_height, ImagesUsedDict, row, col, spacing):
    '''
    takes target color in HSV array and iterates through library to find best color tile

    requires the database and MosaicColors Table

    issue:
    have problem when there multiple printings of the same art

    TODO:
    Add logic for ImagesUsedDict to include Card name and then limit same card name to spacing
    '''

    query = "SELECT * from MosaicColors"
    c = DBconnection.cursor()
    c.execute(query)
    potentialTiles = c.fetchall()
    cardIDfinal = 0
    comp = 10000
    #print(targetColor)

    for image in list(ImagesUsedDict):
        if row - ImagesUsedDict[image][0] >= spacing & col - ImagesUsedDict[image][1] >= spacing:
            del ImagesUsedDict[image]
    
    for x in potentialTiles:
        cardID = x[1]
        cardName = x[5]
        H = x[2] 
        S = x[3]
        V = x[4]
        tH = targetColor[0]
        tS = targetColor[1]
        tV = targetColor[2]
        
        if comp >= compareHSV(targetColor, [H, S, V]) and (cardName not in ImagesUsedDict):
            comp = compareHSV(targetColor, [H, S, V])
            c.execute("SELECT name, image from cards where id = " + str(cardID))
            test = c.fetchall()

            #Troubleshooting
            #print(test[0][0], '---', abs(tH-H), abs(tS-S), abs(tV-V), '---',str(round(comp,3)))

            im = Image.open(BytesIO(base64.b64decode(test[0][1])))
            cardNamefinal = cardName
        if comp == 0:
            break

    
    #print(cardIDfinal)
    ImagesUsedDict[cardNamefinal] = [row,col]

    BestTile = ResizeImageForPixel(cropArtModern(im), pix_width, pix_height)
    #BestTile.show()
    #BestTile.save(str(test[0][0]), 'PNG')
    return BestTile


def PreprocessHSVvalues(tileWidth, RebuildAll = False):
    '''

    Build the preprocess table

    TODO:
    handle logic for creating the table in separate function

    '''
    conn = sqlite3.connect('CurrentBuild/mtgDB.db')
    c = conn.cursor()

    if RebuildAll == True:
        c.execute('drop table MosaicColors')
        c.execute('''
            CREATE TABLE if not exists MosaicColors (
                id   INTEGER       UNIQUE
                               PRIMARY KEY
                               NOT NULL,
            CardID INTEGER,
            Hval INTEGER,
            Sval INTEGER,
            Vval INTEGER,
            cardName VARCHAR (256),
            set_code VARCHAR (12)
            )
        ''')
        conn.commit()

    valid_sets = ['8ED','MRD','DST','5DN','CHK','UNH','BOK','SOK','9ED','RAV','GPT','DIS','CSP',
    'TSP','PLC','FUT','10E','MED','LRW','EVG','MOR','SHM','EVE','DRB','ME2',
    'ALA','DD2','CON','DDC','ARB','M10','TD0','V09','HOP','ME3','ZEN','DDD',
    'H09','WWK','DDE','ROE','DPA','ARC','M11','V10',
    'DDF','SOM','TD0','PD2','ME4','MBS','DDG','NPH',
    'CMD','M12','V11','DDH','ISD','PD3','DKA','DDI',
    'AVR','PC2','M13','V12','DDJ','RTR','CM1','TD2',
    'GTC','DDK','DGM','MMA','M14','V13','DDL','THS',
    'C13','BNG','DDM','JOU','MD1','CNS','VMA','M15',
    'V14','DDN','KTK','C14','DD3','FRF','DDO','DTK',
    'TPR','MM2','ORI','V15','DDP','BFZ','EXP','C15',
    'PZ1','OGW','DDQ','W16','SOI','EMA','EMN','V16',
    'CN2','DDR','KLD','MPS','PZ2','C16','PCA',
    'AER','MM3','DDS','W17','AKH','MP2','CMA','E01',
    'HOU','C17','XLN','DDT','IMA','E02','V17','UST',
    'RIX','A25','DDU','Q01','DOM','CM2','BBD','SS1',
    'GS1','M19','C18','MED','GRN','SK1','GK1','GNT',
    'UMA','MED','RNA','GK2','Q02','MED','WAR','MH1',
    'SS2','M20','C19','ELD','GN2','SLD','THB','SLD',
    'SLD','UND','SLD','SLD','Q03','IKO','C20','SLD',
    'SLD','SLU','SS3','M21']


    for x in valid_sets:
        c.execute('DELETE  from MosaicColors where  set_code = \'' + x + '\'')
        
        c.execute('SELECT id, name, image, set_code from cards where image != \'No Image Available\' and layout  in (\'normal\', \'leveler\', \'transform\' , \'adventure\' ,\'meld\', \'host\', \'augment\') and set_Code = \'' + x +  '\'')
        cards = c.fetchall() 

        print('Adding Set: ' + x)
        for y in cards:
            #creates PIL object with image
            im = Image.open(BytesIO(base64.b64decode(y[2])))
            
            # Here the image "im" is cropped and assigned to new variable im_crop
            width, height = im.size
            (left, upper, right, lower) = (width*.092, height*.13, width*.908, height*.55)
            im_crop = im.crop((left, upper, right, lower))

            #resize for Mosaic Preprocess
            tileHeight = round(tileWidth/1.391)
            im_crop.resize((tileWidth, tileHeight))

            #If you want to save the image to a file
            #im_crop.save(str(y[1]), 'PNG') 
            #print(im_crop.size)

            #print(bm.getImageAvgHSV(im_crop))
            HSV = getImageAvgHSV(im_crop)

            #write values to MosaicColors table
            c.execute("INSERT INTO MosaicColors VALUES (?,?,?,?,?,?,?)", (None, y[0], HSV[0], HSV[1], HSV[2], y[1], x))

    conn.commit()

def BuildMosaicMTG(TargetImage,  pix_width=10, rescale_mod = .2, show = False):
    '''
    This is the function to build the mosaic

    Steps:
    1. Open the target image
    2. Resize to desired dimensions
    3. Divide the image into TILES
    4. Find best Tile
    5. insert into image
    6. repeat 
    7. spit out final image

    '''
    
    #get the image
    im = Image.open(TargetImage)

    #resize our image
    width, height = im.size
    width_mod = round(width * rescale_mod)
    height_mod = round(height * rescale_mod)
    im = im.resize((width_mod,height_mod))
    width, height = im.size

    #divide up image into TILES
    #
    #8ED images are 181 x 130
    #newer frame is 217 x 156
    # 1.391 is ratio of width/height for magic art frames
    # we round the result to make it an integer
    # we will resize the tile image to match this
    
    pix_height = round(pix_width/1.25)
    tilesPerRow = round(width/pix_width)
    tilesPerCol = round(height/pix_height)

    pix = im.load()

    #Connect to DB
    conn = sqlite3.connect('CurrentBuild/mtgDB.db')

    #to prevent image repeating issues:
    #key = cardID and values are [x,y]
    ImagesUsed = {}

    #iterate through tiles in a Row
    for x in range(0, tilesPerRow-1):
        print('building row: ' + str(x+1) + ' of ' + str(tilesPerRow-1) )
        #iterate through each column in that
        for y in range(0, tilesPerCol-1):
            #h_total = 0
            #s_total = 0
            #v_total = 0
            curr_x = x * pix_width
            curr_y = y * pix_height
            max_x = 0
            max_y = 0

            #pix_count = 0

            #handle the edge cases (literally the edge)
            if curr_x + pix_width > width or x == tilesPerRow-1:
                max_x = width
            else:
                max_x = curr_x + pix_width
            #handle the edge cases (literally the edge)
            if curr_y + pix_height > height or y == tilesPerCol-1:
                max_y = height
            else:
                max_y = curr_y +  pix_height


            if (((max_x - curr_x) < pix_width) or ((max_y - curr_y) < pix_height)):
                adj_width = max_x - curr_x
                adj_height = max_y - curr_y
            else: 
                adj_width = pix_width
                adj_height = pix_height

            region = im.crop((curr_x,curr_y,max_x,max_y))
            region_HSV = getImageAvgHSV(region)

            tile = findBestTileMTG(region_HSV, conn, adj_width, adj_height, ImagesUsed, x, y, 5)

            if adj_width == pix_width and adj_height == pix_height:
                im.paste(tile, (curr_x,curr_y,max_x,max_y))
            else:
                continue

    #CROP function here to remove remainder of image, should be less than the width or height of a tile
    im = im.crop((0,0, (tilesPerRow-1)*pix_width, (tilesPerCol-1)*pix_height))

    #Show the image
    if show == True:
        im.show()
    #print(ImagesUsed)

    return im


########################################

# Build the Mosaic here

########################################

#PreprocessHSVvalues(40)

BuildMosaicMTG('Narset1_Upscaled.png', pix_width = 20, rescale_mod = 1, show=False).save('Narset-20-20200703', 'PNG')


########################################

# Tests and Preprocess

########################################

#Preprocesses tile images
#Note this takes awhile but should only need to be done once on the Database
#PreprocessHSVvalues(40)

#test colors
# targetColor = [359, 32, 100]
# pix_width = 100
# pix_height = 70

#display the closest match
# findBestTileMTG(targetColor, conn, 100, 70).show()