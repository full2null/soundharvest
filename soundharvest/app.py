from os import remove
from pathlib import Path
from typing import Any

import streamlit as st
from streamlit.delta_generator import DeltaGenerator
from streamlit.runtime.state.session_state_proxy import SessionStateProxy
from yt_dlp import DownloadError, YoutubeDL


class QuietLogger:
    def debug(self, message: str) -> None:
        pass

    def info(self, message: str) -> None:
        pass

    def warning(self, message: str) -> None:
        pass

    def error(self, message: str) -> None:
        pass


def format_codec(option: str) -> str:
    match option:
        case "mp3":
            return "MP3"

        case "aac":
            return "AAC"

        case "opus":
            return "Opus"


def format_quality(option: str) -> str:
    match option:
        case "0":
            return "High"

        case "2":
            return "Medium"

        case "4":
            return "Low"


def on_download() -> None:
    # TODO: try / except
    remove(f"cache/{filename}")


def on_url_change() -> None:
    state["extracted_info"]: dict[str, Any] | None = None


def sanitize_filename(filename: str) -> str:
    replace_mapping: dict[str, str] = {
        "\\": "＼",
        "/": "⧸",
        ":": "：",
        "*": "＊",
        "?": "？",
        '"': "＂",
        "<": "＜",
        ">": "＞",
        "|": "｜",
    }

    for char, replacement in replace_mapping.items():
        filename: str = filename.replace(char, replacement)

    return filename


st.set_page_config(
    page_title="SoundHarvest",
    page_icon=":musical_note:",
    menu_items={
        "About": "Harvest audio files from YouTube, using yt-dlp.",
    },
)

state: SessionStateProxy = st.session_state

if "cbr" not in state:
    state["cbr"]: str = ""

if "codec" not in state:
    state["codec"]: str = ""

if "extracted_info" not in state:
    state["extracted_info"]: dict[str, Any] | None = None

if "quality" not in state:
    state["quality"]: str = ""

if "ydl_options" not in state:
    state["ydl_options"]: dict[str, Any] = {
        "final_ext": None,
        "format": "ba/b",
        "logger": QuietLogger(),
        "outtmpl": {"default": "cache/%(title)s.%(ext)s", "pl_thumbnail": ""},
        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "nopostoverwrites": False,
                "preferredcodec": None,
                "preferredquality": None,
            },
            {
                "add_chapters": True,
                "add_infojson": "if_exists",
                "add_metadata": True,
                "key": "FFmpegMetadata",
            },
            {"already_have_thumbnail": False, "key": "EmbedThumbnail"},
        ],
        "quiet": True,
        "writethumbnail": True,
    }

st.title("SoundHarvest", anchor=False)

url: str = st.text_input(
    "YouTube URL",
    on_change=on_url_change,
    placeholder="Enter YouTube URL...",
    label_visibility="collapsed",
)

if url:
    ydl_options: dict[str, Any] = state["ydl_options"]

    try:
        if state["extracted_info"] is None:
            with YoutubeDL(ydl_options) as ydl:
                state["extracted_info"]: dict[str, Any] | None = ydl.extract_info(
                    url, download=False
                )

        thumbnail_url: str = state["extracted_info"]["thumbnail"]
        title: str = state["extracted_info"]["title"]
        uploader: str = state["extracted_info"]["uploader"]

        st.image(thumbnail_url)
        st.subheader(title, anchor=False)
        st.write(uploader)

        state["codec"]: str = st.radio(
            "Codec",
            ["mp3", "aac", "opus"],
            format_func=format_codec,
            horizontal=True,
        )
        state["quality"]: str = st.radio(
            "Quality",
            ["0", "2", "4"],
            format_func=format_quality,
            help="Currently not working on Opus codec.",
            horizontal=True,
        )
        # TODO: Add description about CBR
        state["cbr"]: bool = st.toggle(
            "Enable CBR",
            help="Currently not working on Opus codec.",
        )

        placeholder: DeltaGenerator = st.empty()

        if placeholder.button("Extract"):
            with st.spinner("Extracting..."):
                placeholder.button(
                    "Extract",
                    key="extracting",
                    disabled=True,
                )

                ydl_options["postprocessors"][0]["preferredcodec"]: str = state["codec"]
                ydl_options["postprocessors"][0]["preferredquality"]: str = state[
                    "quality"
                ]

                if state["cbr"]:
                    match state["quality"]:
                        case "0":
                            ydl_options["postprocessors"][0][
                                "preferredquality"
                            ]: str = "320"

                        case "2":
                            ydl_options["postprocessors"][0][
                                "preferredquality"
                            ]: str = "192"

                        case "4":
                            ydl_options["postprocessors"][0][
                                "preferredquality"
                            ]: str = "128"

                with YoutubeDL(ydl_options) as ydl:
                    ydl.download([url])

            match state["codec"]:
                case "mp3":
                    extension: str = "mp3"
                    mime: str = "mpeg"

                case "aac":
                    extension: str = "m4a"
                    mime: str = "aac"

                case "opus":
                    extension: str = "opus"
                    mime: str = "opus"

            filename: str = sanitize_filename(f"{title}.{extension}")

            with open(Path(f"./cache/{filename}"), "rb") as f:
                placeholder.download_button(
                    "Download",
                    data=f,
                    file_name=filename,
                    mime=f"audio/{mime}",
                    on_click=on_download,
                )

    except DownloadError as e:
        if "not a valid URL" in e.msg:
            st.error(f"'{url}' is not a valid URL.")

        elif "Video unavailable" in e.msg:
            st.error("Video unavailable.")

        else:
            # TODO: More detailed error message
            st.error("An error occurred.")
