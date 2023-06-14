from PIL import Image, ImageChops, ImageFilter
# sprites-making tool by ShereKhanRomeo
# this code is free to use, change and post anywhere as I don't care XD

background_pic = '25.webp'
pics_to_be_converted_into_sprites = [
    '26.webp',
    '27.webp',
    '28.webp',
    '29.webp',
    '30.webp',
    '31.webp'
]

# left empty to not change file format
save_output_files_as = "" # ".png" < example in case you need to change it

# make sure those end with /
_take_original_pics_from = 'D:/folder_to_get_pics_from/'
_place_only_changed_sprites_into = 'D:/output_folder/'

# how sharp sprites contours are meant to be.
# 0 - is "turned off", sprites will contain lot of noise, but result in more smoothness
# 1.5 - recommended
# 7 - sharp, less noise, sprites are like cut out from paper with scissors
_sharpness_lvl = 1.5

# cleanses too small differences
# 0 - cleans nothing
# 1 - recommended
# 20 and higher are not recommended
# values higher than 100 are not tested
_noise_threshold = 1

# saves masks as a separate file alongside processed pics
# red color shows which pixels will be saved from original pic and other pixels will be transparent
# left here to let you experiment with settings and see what suits better for your needs
_save_masks_preview = True


def processPicsWithNoiseThreshold(_bgPic, _spritePic):
    from PIL import Image, ImageChops, ImageFilter
    bg = Image.open(_take_original_pics_from + _bgPic)
    sprite = Image.open(_take_original_pics_from + _spritePic)
    diff1 = ImageChops.difference(bg, sprite).convert('RGBA').filter(ImageFilter.GaussianBlur(_sharpness_lvl))
    newimdata = []
    dat = diff1.getdata()
    for color in dat:
        if color[0] + color[1] + color[2] <= _noise_threshold:
            newimdata.append((0, 0, 0, 0))
        else:
            newimdata.append((255, 0, 0, 255))
    mask = Image.new('RGBA', diff1.size)
    mask.putdata(newimdata)
    picName = _spritePic
    if len(save_output_files_as) >=1:
        picName = _spritePic.partition('.')[0] + save_output_files_as
    if _save_masks_preview:
        mask.save(_place_only_changed_sprites_into + 'diff' + picName)
    ImageChops.composite(sprite, Image.new("RGBA", sprite.size, 0), mask) \
        .save((_place_only_changed_sprites_into + picName), compress_level = 6, lossless=True, quality=95, method=6)
    # regarding save options:
    # Only matters when saving in PNG:
    # compress_level (default is 6, 0 - no compression, 1 is fastest and 9 is best compression

    # Only matters when saving in WEBP:
    # lossless (if True, switches to lossless compression and makes "quality" param be 0-no compression, 100- max compression)
    # quality (if lossless is False, 0 gives the smallest size and 100 the largest)
    # method (quality/speed trade-off (0=fast, 6=slower but better), defaults to 4)
    print(picName + " is ready...")

print("Converting {0} pics into sprites...".format(len(pics_to_be_converted_into_sprites)))
for sprite in pics_to_be_converted_into_sprites:
    processPicsWithNoiseThreshold(background_pic, sprite)
print("Done!")
