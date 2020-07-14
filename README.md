

# Mosaic Builder in Python using MTG art
### Under Construction

##### Prerequisites

1. Libraries (to be added)

##### How to use

1. Create Database using the DB scripts (to be added)
2. Preprocess Color Values table (to be added)
3. Run the following :

BuildMosaicMTG(sourceFileName, pix_width = 20, rescale_mod = 1, show=False).save(OutputFileName, OutPutImageFormat)


**sourceFileName** == The image you want to turn into a mosaic
**pix_width** == width of indvidual mosaic tiles, height is based off of this value to maintain normal aspect ratio, default is 20
**rescale_mod** == modification to output image size comparted to source, default is 1
**show** == True/False to display the image after completion, default is False
**OutputFileName** == File name of output
**OutPutImageFormat** == Image format of output (PIL)

**Example:**
BuildMosaicMTG('Narset1_Upscaled.png', pix_width = 20, rescale_mod = 1, show=False).save('Narset-20pixTiles', 'PNG')
