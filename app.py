import time
import streamlit as st
import os
from pytubefix import YouTube
from moviepy import VideoFileClip
import re
import base64

# Create directories if they don't exist
if not os.path.exists("youtube_videos"):
    os.makedirs("youtube_videos")
if not os.path.exists("trimmed_videos"):
    os.makedirs("trimmed_videos")


def get_binary_file_downloader_html(file_path, file_label):
    """Generate download button HTML for a file"""
    with open(file_path, "rb") as f:
        data = f.read()
    b64 = base64.b64encode(data).decode()
    download_filename = os.path.basename(file_path)
    href = f'<a href="data:video/mp4;base64,{b64}" download="{download_filename}"><button style="padding: 5px 10px; background-color: #4CAF50; color: white; border: none; border-radius: 4px; cursor: pointer;">Download {file_label}</button></a>'
    return href


def sanitize_filename(filename):
    """Remove invalid characters from filename"""
    return re.sub(r'[<>:"/\\|?*]', "", filename)


def download_youtube_video(url):
    """Download YouTube video and return the path"""
    try:
        yt = YouTube(url)
        video = (
            yt.streams.filter(progressive=True, file_extension="mp4")
            .order_by("resolution")
            .desc()
            .first()
        )
        if not video:
            st.error("No suitable video stream found")
            return None, None

        filename = sanitize_filename(yt.title)
        # Download to youtube_videos directory with proper filename
        video.download(output_path="youtube_videos", filename=f"{filename}.mp4")
        output_path = os.path.join("youtube_videos", f"{filename}.mp4")

        # Verify download was successful
        max_attempts = 10
        attempts = 0
        while not os.path.exists(output_path) and attempts < max_attempts:
            time.sleep(1)
            attempts += 1

        if not os.path.exists(output_path):
            st.error("Download failed - file not created")
            return None, None

        return output_path, filename
    except Exception as e:
        st.error(f"Error downloading video: {str(e)}")
        return None, None


def trim_video(video_path, filename, segment_duration):
    """Trim video into segments of specified duration"""
    if not os.path.exists(video_path):
        st.error(f"Video file not found: {video_path}")
        return []

    video = None
    try:
        video = VideoFileClip(video_path)
        total_duration = video.duration
        num_segments = int(total_duration // segment_duration) + (
            1 if total_duration % segment_duration > 0 else 0
        )

        # Create directory for trimmed segments
        output_dir = os.path.join("trimmed_videos", sanitize_filename(filename))
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        trimmed_paths = []
        # Create a progress bar
        progress_bar = st.progress(0)

        for i in range(num_segments):
            start_time = i * segment_duration
            end_time = min((i + 1) * segment_duration, total_duration)

            segment = video.subclipped(start_time, end_time)
            output_path = os.path.join(output_dir, f"part_{i+1}.mp4")
            segment.write_videofile(output_path, codec="libx264", audio_codec="aac")
            trimmed_paths.append(output_path)

            # Update progress
            progress = (i + 1) / num_segments
            progress_bar.progress(progress)

        return trimmed_paths
    except Exception as e:
        st.error(f"Error trimming video: {str(e)}")
        return []
    finally:
        if video is not None:
            video.close()


# Streamlit UI
st.title("YouTube Video Trimmer")
st.write("Enter a YouTube video URL and specify the duration for each segment.")

# Input fields
youtube_url = st.text_input("YouTube Video URL")
segment_duration = st.number_input("Segment Duration (seconds)", min_value=1, value=60)

if st.button("Process Video"):
    if youtube_url:
        with st.spinner("Downloading video..."):
            video_path, video_filename = download_youtube_video(youtube_url)

        if video_path and video_filename:
            st.success("Video downloaded successfully!")

            with st.spinner("Trimming video..."):
                trimmed_paths = trim_video(video_path, video_filename, segment_duration)

            if trimmed_paths:
                st.success(
                    f"Video trimmed successfully into {len(trimmed_paths)} segments!"
                )

                # Display video gallery
                st.header("Video Gallery")
                st.write(
                    "Click on any video to play, or use the download button to save it."
                )

                # Create columns for the gallery layout
                cols_per_row = 2
                for i in range(0, len(trimmed_paths), cols_per_row):
                    cols = st.columns(cols_per_row)
                    for j, col in enumerate(cols):
                        if i + j < len(trimmed_paths):
                            with col:
                                video_path = trimmed_paths[i + j]
                                st.video(video_path)
                                st.markdown(
                                    get_binary_file_downloader_html(
                                        video_path, f"Part {i + j + 1}"
                                    ),
                                    unsafe_allow_html=True,
                                )
                                st.write(f"Duration: {segment_duration} seconds")

                # Optional: Clean up the source video
                # try:
                #     os.remove(video_path)
                # except Exception as e:
                #     st.warning(f"Could not remove source video: {str(e)}")
    else:
        st.warning("Please enter a YouTube video URL")
