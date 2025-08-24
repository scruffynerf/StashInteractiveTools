from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from assets.config import Config

import json
import sys
import os
import re
import shutil
import math
import hashlib
from datetime import timedelta
from PIL import Image, ImageDraw, ImageFont
from typing import Dict, Any

import time
config:'Config'

SCENE_FRAGMENT = """
id
title
files {
 path
 duration
 fingerprint(type: "oshash")
}
"""
background = (0,0,0,255)
dupebackground = (255,255,255,255)

def dict_hash(dictionary: Dict[str, Any]) -> str:
    """MD5 hash of a dictionary."""
    dhash = hashlib.md5()
    # We need to sort arguments so that
    # {'a': 1, 'b': 2} is the same as
    # {'b': 2, 'a': 1}
    encoded = json.dumps(dictionary, sort_keys=True).encode()
    dhash.update(encoded)
    return dhash.hexdigest()

def lerp(a: int, b: int, t: float):
    """Linear interpolate on the scale given by a to b, using t as the point on that scale.
    """
    return int((1 - t) * a + t * b)

def colorlerp(a, b, t):
    r = lerp(a[0],b[0],t)
    g = lerp(a[1],b[1],t)
    b = lerp(a[2],b[2],t)
    return (r,g,b,255)

#def speedtocolor(speed):
#    heatmap = [
#    [0, 0, 0],
#    [30, 144, 255],
#    [34, 139, 34],
#    [255, 215, 0],
#    [220, 20, 60],
#    [128, 0, 128],
#    (48, 64, 77),
#    ]
#    stepsize = 120
#    if speed <= 0.001:
#       c = heatmap[6]
#    elif speed <= 1*stepsize:
#       f = speed / stepsize
#       c = colorlerp(heatmap[1],heatmap[2],f)
#    elif speed <= 2*stepsize:
#       f = (speed - 1*stepsize) / stepsize
#       c = colorlerp(heatmap[2],heatmap[3],f)
#    elif speed <= 3*stepsize:
#       f = (speed - 2*stepsize) / stepsize
#       c = colorlerp(heatmap[3],heatmap[4],f)
#    elif speed <= 4*stepsize:
#       f = (speed - 3*stepsize) / stepsize
#       c = colorlerp(heatmap[4],heatmap[5],f)
#    else:
#       f = min((speed - 4*stepsize) / (5 * stepsize),1)
#       c = colorlerp(heatmap[5],heatmap[0],f)
#    return c

def speedtocolor(speed):
    # Match JS palette exactly
    heatmap = [
        [0, 0, 0],
        [30, 144, 255],
        [34, 139, 34],
        [255, 215, 0],
        [220, 20, 60],
        [147, 112, 219],
        [37, 22, 122],
    ]
    stepsize = 120

    # Clamp to black if <= 0
    if speed <= 0:
        return (*heatmap[0], 255)

    # Clamp to final color if > 600
    if speed > 600:
        return (*heatmap[6], 255)

    # JS adds 60 before dividing into bins
    speed += 60

    # Determine indices
    lower_index = int(speed // stepsize)
    upper_index = lower_index + 1
    frac = min(1.0, max(0.0, (speed - lower_index * stepsize) / stepsize))

    # Get the two colors
    c1 = heatmap[lower_index]
    c2 = heatmap[upper_index]

    # Interpolate between them
    r = int(c1[0] + (c2[0] - c1[0]) * frac)
    g = int(c1[1] + (c2[1] - c1[1]) * frac)
    b = int(c1[2] + (c2[2] - c1[2]) * frac)

    return (r, g, b, 255)

def opposite_color(color):
    r, g, b, a = color
    return (255 - r, 255 - g, 255 - b, a)

def opposite_readable(color):
    r, g, b, a = color
    return (r, g, b, 225)

def ms_to_time(ms: int) -> str:
    td = timedelta(milliseconds=ms)
    total_seconds = int(td.total_seconds())
    hours, remainder = divmod(total_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    if hours:
        return f"{hours}:{minutes:02d}:{seconds:02d}"
    return f"{minutes}:{seconds:02d}"

def make_heatmap(funscriptpath, heatmappath, sceneduration, text, backgroundcolor=(0,0,0,255)):

   # Original python heatmap code based on concepts in js code by Lucife and defucilis and stashapp

   # read the funscript
   try:
     with open(funscriptpath, 'br') as fun_file:
        fun_data = json.load(fun_file)

   except json.JSONDecodeError as e:
     config.log.error(f"Error: {funscriptpath} file is not valid JSON ({e})")
     shutil.copyfile(os.path.join(os.path.dirname(__file__), "./broken.png"), heatmappath)

   except OSError as e:
     config.log.error(f"Error: Could not open {funscriptpath} ({e})")
     shutil.copyfile(os.path.join(os.path.dirname(__file__), "./missing.png"), heatmappath)

   action_length = len(fun_data['actions'])
   # log.debug(f"action length = {action_length}")

   # use actual duration of video length to ensure all align
   script_duration = fun_data['actions'][-1]["at"]

   last_time  = sceneduration * 1000
   if last_time == 0:
      last_time = script_duration
      if last_time < 0:
         last_time = 10000

   #   log.debug(f"overflow in {funscriptpath}")
   # log.debug(f"total length in time = {last_time}")

   # size of image
   width = 320
   height = 15

   # init canvas
   im = Image.new('RGBA', (width, height), backgroundcolor)
   draw = ImageDraw.Draw(im)

   font_path = os.path.join(os.path.dirname(__file__), "voltergoldfish.ttf")
   font = ImageFont.truetype(font_path, 9)

   #blocksize = (last_time) / width
   # log.debug(f"blocksize: {blocksize}")
   #avgpos = action_length/width

   #positions = {}
   #speeds = {}
   #intensitys = {}
   #for column in range(0, width+1):
   #    positions["column" + str(column)] = []
   #    speeds["column" + str(column)] = []
   #    intensitys["column" + str(column)] = []

   #prev_item = []
   #firstitem = True
   #maxspeed = 0
   #maxintensity = 0

   #for action_item in fun_data['actions']:
   #    at_time = action_item["at"]
   #    position = action_item["pos"]
   #    column = math.floor(at_time/blocksize)
   #    if column >= 0 and column < 320:
   #      columnstr = "column" + str(column)
   #      positions[columnstr].append(position)
   #      if firstitem:
   #         firstitem = False
   #         prev_item = action_item
   #      else:
   #         t1 = at_time
   #         t2 = prev_item["at"]
   #         p1 = position
   #         p2 = prev_item["pos"]
   #         if t1 is not None and t2 is not None and p1 is not None and p2 is not None:
   #            if t1 != t2:
   #               # slope = min( max( 1/(2*(t1-t2)/1000), 0), 20)
   #               # intensity = int(slope * abs(p1-p2))
   #               # intensitys[columnstr].append(intensity)
   #               # if intensity > maxintensity:
   #               #   maxintensity = intensity
   #               speed = abs(p1-p2) / (t1-t2) * 1000
   #               speeds[columnstr].append(speed)
   #               if speed > maxspeed:
   #                  maxspeed = speed
   #               prev_item = action_item

   #previousspeed = 0
   #tophalf = 0
   #bottomhalf = height - 1
   #color = backgroundcolor
   #for column in range(0,width-1):
   #    columnstr = "column" + str(column)
   #    # log.debug(f"{column} positions {positions[columnstr]}")
   #    # log.debug(f"{column} speeds {speeds[columnstr]}")
   #    # log.debug(f"{column} intensity {intensitys[columnstr]}")
   #    if len( positions[columnstr] ):
   #       allpos = sorted(positions[columnstr])
   #       middle_index = int(len(allpos)/2 + .5)
   #       if middle_index > 0:
   #          bottomhalf = 0
   #          if len(allpos[:middle_index]) > 0:
   #             valid_vals = [x for x in allpos[:middle_index] if isinstance(x, (int, float))]
   #             if valid_vals:
   #                bottomhalf = int(height * (1 - (sum(valid_vals) / len(valid_vals)) / 100))
   #          tophalf = 0
   #          if len(allpos[middle_index:]) > 0:
   #             valid_vals = [x for x in allpos[middle_index:] if isinstance(x, (int, float))]
   #             if valid_vals:
   #                tophalf = int(height * (1 - (sum(valid_vals) / len(valid_vals)) / 100))
   #          if len(speeds[columnstr]) > 0:
   #             speed =  sum(speeds[columnstr])/len(speeds[columnstr])
   #             # speed =  statistics.median(speeds[columnstr])
   #             # speedmode =  statistics.mode(speeds[columnstr])
   #             # speedmean =  statistics.mean(speeds[columnstr])
   #             speedcolor = int((250 - speed * 360/maxspeed)%360)
   #             # speedcolor2 = int((230 - speed * 360/maxspeed)%360)
   #             # speedcolor2 = speedtocolor(speed)
   #             # previousspeed = speed
   #             # intensity = maxintensity/sum(intensitys['column' + str(column)])/(len(intensitys['column' + str(column)])+.01)
   #          else:
   #             speed = 0
   #             speedcolor = 0
   #          # adjustcolor = int(max(min(50 + ((len(allpos) - avgpos)/avgpos * 10),25),75))
   #          color = "hsl(" + str(speedcolor) + ",100%, 50%)"
   #         # color1 = "hsl(" + str(speedcolor2) + ",100%, 50%)"
   #          # log.debug(f"column {column}: top:{tophalf} bottom:{bottomhalf} speed: {speed}, color: {color}")
   #          draw.line( [column,tophalf,column,bottomhalf],color)
   #          # draw.line( [column,tophalf+15,column,bottomhalf+15],color1)
   #       else:
   #          draw.line( [column,tophalf,column,bottomhalf],color)
   #          tophalf = 0
   #          bottomhalf = 0
   #          color = backgroundcolor
   #    else:
   #       draw.line( [column,tophalf,column,bottomhalf],color)
   #       tophalf = 0
   #       bottomhalf = 0
   #       color = backgroundcolor

   actions = fun_data['actions']

   # scaling factor

   # funscript that fits scene duration
   xscale = width / (sceneduration * 1000)

   # funscript always in full
   # xscale = width / actions[-1]["at"]

   speeds, positions = [], []
   m = 0  # previous x pixel

   for i in range(1, len(actions)):
        prev = actions[i - 1]
        curr = actions[i]

        b = int(xscale * curr["at"])  # current x pixel

        # Compute speed
        dt = curr["at"] - prev["at"]
        dp = curr["pos"] - prev["pos"]
        if dt > 0:
            speed = abs(dp) / dt * 1000
            speeds.append(speed)
            if len(speeds) > 50:
                speeds.pop(0)

        # Push positions (limit 15)
        positions.append(curr["pos"])
        if len(positions) > 15:
            positions.pop(0)

        if speeds:
            avg_speed = sum(speeds) / len(speeds)
            color = speedtocolor(avg_speed)
        else:
            color = (0, 0, 0, 255)

        # Split positions into halves
        sorted_pos = sorted(positions)
        mid = len(sorted_pos) // 2
        lower = sorted_pos[:mid] or [0]
        upper = sorted_pos[mid:] or [100]

        I = sum(lower) / len(lower)
        j = sum(upper) / len(upper)

        N = height * (I / 100.0)
        R = height * (j / 100.0)

        # Draw rectangle
        draw.rectangle([min(m, b), min(height - N, height - R),
                max(m, b), max(height - N, height - R)], fill=color)

        m = b

   # Position (x, y) in pixels from top-left corner
   x, y = 2, 2
   bbox = draw.textbbox((x, y), text, font=font)  # (left, top, right, bottom)
   draw.rectangle(bbox, fill=opposite_readable(backgroundcolor))
   draw.text((x, y), text, font=font, fill=opposite_color(backgroundcolor))

   # Get bounding box of duration
   timetext = ms_to_time(int(script_duration))
   bbox = draw.textbbox((0, 0), timetext, font=font)  # (left, top, right, bottom)
   text_width = bbox[2] - bbox[0]
   text_height = bbox[3] - bbox[1]
   # Compute position (aligned right, 2px margin)
   x = width - text_width - 2
   y = 2
   bbox_at_pos = (x-1, y-1, x + text_width+1, y + text_height+1)
   draw.rectangle(bbox_at_pos, fill=opposite_readable(backgroundcolor))
   draw.text((x, y), timetext, font=font, fill=opposite_color(backgroundcolor))

   # save image
   # log.debug(heatmappath)
   im.save(heatmappath)

   return

def remap_scene(scene, funscripts, genpath):
   sceneduration = scene['files'][0]['duration']
   scenehash = scene['files'][0]['fingerprint']
   heatmappath = genpath + "/interactive_heatmaps/" + scenehash + ".png"

   images_list = []
   action_list = []
   funscriptcount = len(funscripts)
   funcount = 0
   sorting_funscripts = {}
   # presort
   for funscript in funscripts:
       funcount += 1
       label = ""
       if os.path.isfile(funscript):
          scenepath = os.path.splitext(os.path.basename(scene['files'][0]['path']))[0]
          funlabel = os.path.splitext(os.path.basename(funscript))[0]

          # due to the way Stash chokes on generating for primary tokens, we'll check contents here...
          try:
             with open(funscript, 'br') as fun_file:
                  fun_data = json.load(fun_file)
                  if fun_data['actions'][0]["at"] == 66 and fun_data['actions'][1]["pos"] == 83 and fun_data['actions'][2]["pos"] == 84:
                     label = "ZZtoken"
                     if len(funscripts) > 1 and funlabel.startswith(scenepath) and funlabel[len(scenepath):].strip("() ") == "":
                        config.log.info(f"{scene['id']} {scene['title']} has a primary funscript of a token and should be changed...")
                        newpath = os.path.splitext(funscript)[0] + " (token).funscript"
                        if not os.path.isfile(newpath):
                           config.log.info(f"renaming {funscript} to {newpath}")
                           os.rename(funscript, newpath)
                           funscripts.append(newpath)
                           sorting_funscripts[str(newpath)] = label
                           if os.path.isfile(newpath) and not os.path.isfile(funscript):
                              # ok, we moved it, now put a file into it's place as default
                              config.log.info(f"You'll want to rescan, regenerate and run the remap again")
                              if funcount == 1:
                                 # copy the next item
                                 config.log.info(f"copying {funscripts[1]} to {funscript}")
                                 shutil.copyfile(funscripts[1], funscript)
                              else:
                                 # copy the first item
                                 config.log.info(f"copying {funscripts[0]} to {funscript}")
                                 shutil.copyfile(funscripts[0], funscript)
                              label = "default"
                  else:
                     # Remove scenepath from the start of funlabel
                     label = funlabel[len(scenepath):].strip("() ") if funlabel.startswith(scenepath) else funlabel.strip("() ")
                     if label == "":
                           label = "default"
          except json.JSONDecodeError as e:
             config.log.error(f"Error: {funscript} file is not valid JSON ({e})")
             label = "ZZbroken"
          except OSError as e:
             config.log.error(f"Error: Could not open {funscript} ({e})")
             label = "ZZmissing"
       else:
           config.log.error(f"Error: File is missing {funscript}")
           label = "ZZmissing"

       sorting_funscripts[str(funscript)] = label

   # Sort filepaths by label, with 'default' first
   funscripts_sorted = sorted(
        funscripts,
        key=lambda fp: (0 if sorting_funscripts[str(fp)] == "default" else 2 if sorting_funscripts[str(fp)] == "ZZtoken" else 1,  sorting_funscripts[str(fp)] )
   )

   funcount = 0

   for funscript in funscripts_sorted:
       funcount += 1
       heatmap = f"/tmp/{funcount}-{scenehash}.png"

       if os.path.isfile(funscript):
          try:
            with open(funscript, 'br') as fun_file:
               fun_data = json.load(fun_file)
          except json.JSONDecodeError as e:
             config.log.error(f"Error: {funscript} file is not valid JSON ({e})")
             shutil.copyfile(os.path.join(os.path.dirname(__file__), "./broken.png"), heatmap)
             images_list.append(heatmap)
             continue
          except OSError as e:
             config.log.error(f"Error: Could not open {funscript} ({e})")
             shutil.copyfile(os.path.join(os.path.dirname(__file__), "./missing.png"), heatmap)
             images_list.append(heatmap)
             continue
       else:
          shutil.copyfile(os.path.join(os.path.dirname(__file__), "./missing.png"), heatmap)
          config.log.error(f"MISSING: {funscript}")
          images_list.append(heatmap)
          continue

       fun_actions = dict_hash(fun_data['actions'])
       if fun_actions in action_list:
          # we have seen this before, use dupe background
          backcolor = dupebackground
          # this is where we can flag it as a dupe
          #config.log.info(f"{funscript} is a duplicate of one of the other funscripts processed so far")
          #if not os.path.isfile(str(funscript) + "dupe"):
          #   config.log.info(f"we will rename {funscript} to {funscript}dupe")
          #   try:
          #      os.rename(funscript, str(funscript) + "dupe")
          #      continue
          #   except OSError as e:
          #      config.log.error(f"Unable to rename {funscript} to {funscript}dupe")
       else:
           action_list.append(fun_actions)
           backcolor = background

       if fun_data['actions'][0]["at"] == 66 and fun_data['actions'][1]["pos"] == 83 and fun_data['actions'][2]["pos"] == 84:
            config.log.debug(f"token: {funscript}")
            # token - add the token graphic instead
            shutil.copyfile(os.path.join(os.path.dirname(__file__), "./token.png"), heatmap)
            images_list.append(heatmap)
       else:
         text = "default"
         scenepath = os.path.splitext(os.path.basename(scene['files'][0]['path']))[0]
         funlabel = os.path.splitext(os.path.basename(funscript))[0]
         # Remove scenepath from the start of funlabel
         text = funlabel[len(scenepath):].strip("() ") if funlabel.startswith(scenepath) else funlabel.strip("() ")
         if text == "":
            text = "default"
         if len(funscripts_sorted) == 1:
            text = ""

         make_heatmap(funscript, heatmap, sceneduration, text, backcolor)
         images_list.append(heatmap)

   if len(images_list):
      imgs = [Image.open(i) for i in images_list]
      min_img_width = min(i.width for i in imgs)
      total_height = 0
      for i, img in enumerate(imgs):
        # If the image is larger than the minimum width, resize it
        # if img.width > min_img_width:
        #   imgs[i] = img.resize((min_img_width, int(img.height / img.width * min_img_width)), Image.ANTIALIAS)
        total_height += imgs[i].height

      # Now that we know the total height of all of the resized images, we know the height of our final image
      img_merge = Image.new(imgs[0].mode, (min_img_width, total_height))
      y = 0
      for img in imgs:
          img_merge.paste(img, (0, y))
          y += img.height
      img_merge.save(heatmappath)
      config.log.debug(f"{scene['id']} {scene['title']} heatmap created: {heatmappath}")

      # remove the imgs from tmp
      for imagefile in images_list:
          # delete file from tmp
          if os.path.isfile(imagefile):
             os.remove(imagefile)

def remap_scenes():
    page = 1
    total = 100
    seen = 0
    init_task = config.get_task('init')

    fullconfig = config.stash.get_configuration()
    genpath = fullconfig['general']['generatedPath']

    while seen < total:
        total, scenes = config.stash.find_scenes({
            'interactive': True
        }, {
            'page': page,
            'per_page': 100,
            'direction': 'DESC',
            'sort': 'updated_at'
        }, "", SCENE_FRAGMENT, get_count=True)
        seen += len(scenes)
        if not len(scenes):
            break
        for scene in scenes:
            file = scene['files'][0]['path']
            funscripts = init_task.get_funscripts(file)
            config.log.debug(f"Scanning {file} with {len(funscripts)} funscript{'s' if len(funscripts) > 1 else ''}")
            remap_scene(scene, funscripts, genpath)
        config.log.progress(seen/total)
        page += 1

def run(c:'Config'):
    global config
    config = c
    mapc = config.stash.find_plugin_config(config.ID)
    config.log.debug(c)
    config.log.debug(mapc)
    remap_scenes()


