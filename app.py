import logging, os, sys, subprocess
from pathlib import PurePath
from resources.modules import filewalker
from resources.modules import mkvtoolnix
from flask import Flask, jsonify, request
from flask_socketio import SocketIO
from flask_cors import CORS

# For PyInstaller w/SocketIO
from engineio.async_drivers import threading
from engineio import async_threading

"""
--------------------------- INSTANTIATION --------------------------
"""

FileWalker = filewalker.FileWalker()
MKVToolNix = mkvtoolnix.MKVToolNix()
app = Flask(__name__)
app_config = {"host": "0.0.0.0", "port": int(sys.argv[1])}
socketioConfig = {
  "async_mode": "threading",
  "cookie": None, # Disable Flask's session cookie
  "session_cookie": True, # Use a custom session cookie
  "session_cookie_secure": True, # Set the Secure flag
  "session_cookie_samesite": "None" # Set the SameSite attribute
}


"""
-------------------------- DEVELOPER MODE --------------------------
"""
# Developer mode uses app.py
if "app.py" in sys.argv[0]:

  # Update app config
  app_config["debug"] = True

  # CORS settings
  cors = CORS(
    app,
    resources={r"/*": {"origins": "http://localhost*"}},
  )

  # SocketIO CORS config
  socketioConfig["cors_allowed_origins"] = "*"

  # CORS headers
  app.config["CORS_HEADERS"] = "Content-Type"


"""
--------------------------- REST CALLS -----------------------------
"""
# SocketIO
socketio = SocketIO(app, **socketioConfig)


""" Request merge batch:
Merges batch of video/subtitles
files using user-provided options.
"""
@app.route("/supported_languages", methods=["get"])
def get_supported_languages():
  return jsonify(MKVToolNix.get_supported_languages())


""" Request merge batch:
Merges batch of video/subtitles
files using user-provided options.
"""
@app.route("/process_batch", methods=["POST"])
def process_batch():

  # REST call request body
  input_directory = request.json["input"]
  output_directory = request.json["output"]
  settings = request.json["settings"]

  # User settings from request body
  language = settings["language"]
  is_remove_ads = settings["isRemoveAds"]
  is_remove_existing_subtitles = settings["isRemoveExistingSubtitles"]
  is_remove_old = settings["isRemoveOld"]
  is_remove_subtitles = settings["isRemoveSubtitles"]
  is_extract_subtitles = settings["isExtractSubtitles"]
  is_same_as_source = settings["isSameAsSource"]
  is_remember_output_dir = settings["isRememberOutputDir"]
  is_only_video_files = is_extract_subtitles or is_remove_subtitles

  # Get batch of files to process
  batch_data = FileWalker.get_files(
    input_directory,
    is_only_video_files
  )

  batch = batch_data["files"]
  warning = batch_data["warning"]

  # Communicate batch details to front end
  socketio.emit("batch_size", len(batch))

  # Iterate through array of tuples and merge
  for video_input_path, subtitle_input_paths in batch:
    video_name = PurePath(video_input_path).stem
    
    relative_path = ""
    if is_remember_output_dir:
      relative_path = os.path.dirname(
          os.path.relpath(video_input_path, input_directory))

    video_output_path = original_output_path = os.path.join(
        output_directory, relative_path, f"{video_name}"
    )
    subtitle_output_path = original_output_path = os.path.join(
        output_directory, relative_path
    )
    video_output_extension = ".mkv"

    # If output is "same as source"
    if is_same_as_source:

      # Update paths to match current video source directory
      video_output_path = original_output_path = os.path.splitext(
        video_input_path
      )[0]

    # Prevent duplicate file names by adding (#) to name
    video_output_path = FileWalker.get_unique_file_path(video_output_path + video_output_extension)

    # Once final video path is determined, add its extension
    video_output_path += video_output_extension

    # Communicate that directory is being processed to front end
    socketio.emit("processing_subdirectory")

    # If "remove" subtitles
    if is_remove_subtitles:
      MKVToolNix.remove_subtitles(video_input_path, video_output_path)

    # If "extract" subtitles
    elif is_extract_subtitles:
      subtitle_output_directory = None if is_same_as_source else subtitle_output_path
      if subtitle_output_directory:
        os.makedirs(subtitle_output_directory, exist_ok=True)
      MKVToolNix.extract_subtitles(video_input_path, subtitle_output_directory)

    # If "merge" subtitles
    else:
      default_language_track = language["text"]

      # Process batch
      MKVToolNix.add_subtitles(
        is_remove_ads,
        is_remove_existing_subtitles,
        subtitle_input_paths,
        default_language_track,
        video_input_path,
        video_output_path,
      )

    # If remove old, delete original files and directory (if empty after)
    if is_remove_old and not is_extract_subtitles:
      video_directory = PurePath(video_input_path).parent

      # Delete old video file
      os.remove(video_input_path)

      # Rename new video file to match old name (now removed)
      os.rename(video_output_path, f"{original_output_path}.mkv")

      # Delete all old subtitle files
      if subtitle_input_paths is not None: # e.g., not "remove" mode
        for subtitle_input_path in subtitle_input_paths:
          os.remove(subtitle_input_path)

      # Delete video directory if it's now empty
      if len(os.listdir(video_directory)) == 0 and not is_same_as_source:
        os.rmdir(video_directory)

  # Status, warning, and error message handling
  status = "Batch complete"
  error = (
    "No valid files were found in the source directory provided."
    if len(batch) == 0
    else None
  )

  if error is not None:
    status = "Error"

  elif warning is not None:
    status = "Warning"

  # Return results to the front end
  return jsonify({"status": status, "warning": warning, "error": error})


"""
-------------------------- ERROR LOGGING ---------------------------
"""

# Get app data path for error log file
error_log_path = os.path.join(
  os.getenv('APPDATA'),
  'MKVToolNix Batch Tool',
  'error.log'
)

# Create logger object
logger = logging.getLogger(__name__)

# Create file handler and set level to ERROR
handler = logging.FileHandler(error_log_path)
handler.setLevel(logging.ERROR)

# Create formatter
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)

# Add handler to logger
logger.addHandler(handler)

""" Handle errors:
Handles any errors noticed
by logging them into a file
at logs/error.log
"""
@app.errorhandler(AttributeError)
@app.errorhandler(Exception)
@app.errorhandler(FileNotFoundError)
@app.errorhandler(IndexError)
@app.errorhandler(KeyError)
@app.errorhandler(ModuleNotFoundError)
@app.errorhandler(PermissionError)
@app.errorhandler(TypeError)
@app.errorhandler(ValueError)
def handle_error(err):
  # Create logger object
  logger = logging.getLogger(__name__)

  # Log the error
  logger.error(f"Error: {str(err)}")

  # Return a response with an error message
  return jsonify({"error": str(err)}), 500


"""
------------------------- FLASK SETTINGS ---------------------------
"""

""" Get Flask port:
Accepts port as system argument
e.g., `start app.exe 3000`
"""
port = sys.argv[1]

""" Shutdown Flask:
Generic function to shutdown
Flask when Electron app closes.
"""
@app.route("/quit")
def quit():
  socketio.stop()
  shutdown = request.environ.get("werkzeug.server.shutdown")
  shutdown()

  return  jsonify({"status": "Flask server has shut down."}), 200


"""
Start Flask microservice server:
Uses a random port between 3000
and 3999.
"""
if __name__ == "__main__":
  socketio.run(app, **app_config)
