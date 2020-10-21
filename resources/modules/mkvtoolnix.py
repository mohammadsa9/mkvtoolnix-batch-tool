import chardet, fileinput, os, subprocess, sys


""" MKVToolNix:
Wrapper for MKVToolNix to allow
control via Python functions
"""
class MKVToolNix:

  # Function to merge video & subtitle into MKV
  def add_subtitle(
    self,
    is_default_track,
    is_remove_ads,
    is_remove_existing_subtitles,
    subtitle_input_path,
    subtitle_language,
    subtitle_track_name,
    video_input_path,
    video_output_path
  ):

    # MKVToolNix command to use
    mkvtoolnix = os.path.abspath('resources/mkvtoolnix')
    mkv_command = f'cd {mkvtoolnix} && mkvmerge -o'

    # Video file input and output paths
    video_path_info = f'"{video_output_path}" "{video_input_path}"'

    # Update video path info to remove existing subs, if user selected option
    if is_remove_existing_subtitles:
      video_path_info = f'"{video_output_path}" --no-subtitles "{video_input_path}"'

    # Determine if subtitles should play automatically (is default track)
    default_track_setting = ' --default-track 0:true' if is_default_track else ''

    # Subtitle language, track name, and path
    subtitle_language_setting = f'--language 0:{subtitle_language}'
    subtitle_track_settings = f'--track-name 0:{subtitle_track_name}{default_track_setting}'
    subtitle_remove_ad_path = subtitle_input_path
    subtitle_input_path = f'"{subtitle_input_path}"' # Wrap in quotes for spaces in dir names

    # If user wants advertisements removed from subtitle files
    if is_remove_ads:
      self.remove_subtitle_ads(subtitle_remove_ad_path)

    # Finalized command for OS
    os_command = ' '.join([
      mkv_command,
      video_path_info,
      subtitle_language_setting,
      subtitle_track_settings,
      subtitle_input_path
    ])

    # Use command in system
    subprocess.call(os_command, shell=True)

  # Function to create MKV file with subtitles removed from existing video
  def remove_subtitle(
    self,
    video_input_path,
    video_output_path
  ):

    # MKVToolNix command to use
    mkvtoolnix = os.path.abspath('resources/mkvtoolnix')
    mkv_command = f'cd {mkvtoolnix} && mkvmerge -o'

    # Video file input path, option(s), and output path
    video_info = f'"{video_output_path}" --no-subtitles "{video_input_path}"'

    # Finalized command for OS
    os_command = ' '.join([ mkv_command, video_info ])

    subprocess.call(os_command, shell=True)


  """ Remove subtitle ads:
  Function to remove common
  advertisements from subtitle
  files
  """
  def remove_subtitle_ads(
    self,
    subtitle_input_path
  ):

    """
    Encoding must be determined,
    otherwise it can break text
    and add strange characters
    to the file(s)
    """
    # Sniff out encoding method
    with open(subtitle_input_path, 'rb') as f:
      rawdata = b''.join([f.readline() for _ in range(10)])

    # Encoding method and method whitelist
    encoding_method = chardet.detect(rawdata)['encoding']
    encoding_method_whitelist = ['utf8', 'ascii']

    # If encoding method will cause issues, convert it to utf-8
    if encoding_method not in encoding_method_whitelist:

      # Read the old file's content
      with open(subtitle_input_path, encoding=encoding_method) as subtitle_file:
        subtitle_text = subtitle_file.read()

      # Convert to utf-8 and write to file
      with open(subtitle_input_path,'w',encoding='utf8') as subtitle_file:
        subtitle_file.write(subtitle_text)


    """
    Once encoding is worked out
    Sort through each line of
    subtitle file to find and
    replace ads
    """
    # Common (fractional) advertisement text
    ad_text = ['mkv player', 'opensubtitles', 'yify']

    # Iterate through lines of subtitle file
    for line in fileinput.input(subtitle_input_path, inplace=True):

      # Reference lowercase version of line, so search is case insensitive
      line_text = line.lower()

      # If advertisement found
      for text in ad_text:

        # Replace the whole ad line with an empty line
        if text in line_text:
          line = '\n'

      # Write line to file
      sys.stdout.write(line)




"""
TODO: should merge each subtitle
file in directory. Need to find
out way to auto determine language
for multiple subtitle files

* Updates settings to reflect this as an option
* read text in subtitle and use this package?
https://stackoverflow.com/questions/39142778/python-how-to-determine-the-language
"""