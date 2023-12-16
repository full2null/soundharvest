from os import remove
from typing import Any

import streamlit as st
from streamlit.delta_generator import DeltaGenerator
from streamlit.runtime.state.session_state_proxy import SessionStateProxy
from yt_dlp import DownloadError, YoutubeDL


class QuietLogger:
    def debug(self, msg: str) -> None:
        pass

    def warning(self, msg: str) -> None:
        pass

    def error(self, msg: str) -> None:
        pass


def extract_audio(url: str) -> None:
    with YoutubeDL(ydl_options) as ydl:
        ydl.download([url])


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


def on_download() -> None:
    remove(f"cache/{filename}")


ydl_options: dict[str, Any] = {
    "final_ext": "mp3",
    "format": "b",
    "logger": QuietLogger(),
    "outtmpl": {"default": "cache/%(title)s.%(ext)s", "pl_thumbnail": ""},
    "postprocessors": [
        {
            "key": "FFmpegExtractAudio",
            "nopostoverwrites": False,
            "preferredcodec": "mp3",  # state["codec"]
            "preferredquality": "320",  # state["quality"]
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

st.set_page_config(
    page_title="SoundHarvest",
    page_icon=":musical_note:",
    menu_items={
        "Report a bug": "https://github.com/full2null/soundharvest/issues/new/choose",
        "Get help": "https://github.com/full2null/soundharvest",
        "About": "Harvest audio files from YouTube, using yt-dlp.",
    },
)

state: SessionStateProxy = st.session_state

if "codec" not in state:
    state["codec"]: str = ""

if "quality" not in state:
    state["quality"]: str = ""

st.title(
    "SoundHarvest",
    anchor=False,
)

url: str = st.text_input(
    "YouTube URL",
    placeholder="Enter YouTube URL...",
    label_visibility="collapsed",
)

if url:
    with YoutubeDL(ydl_options) as ydl:
        try:
            info: dict[str, Any] = ydl.extract_info(url, download=False)

        except DownloadError:
            st.error(f"'{url}' is not a valid URL.")

        else:
            thumbnail_url: str = info["thumbnail"]
            title: str = info["title"]
            uploader: str = info["uploader"]

            st.image(thumbnail_url)
            st.subheader(
                title,
                anchor=False,
            )
            st.write(uploader)

            # TODO: Not supported yet
            state["codec"]: str = st.radio(
                "Codec",
                ["`MP3`", "`AAC`", "`Opus`"],
                horizontal=True,
            )

            # TODO: Not supported yet
            state["quality"]: str = st.radio(
                "Quality",
                ["`320K`", "`192K`", "`VBR`"],
                horizontal=True,
            )

            placeholder: DeltaGenerator = st.empty()

            if placeholder.button("Extract"):
                placeholder.button(
                    "Extracting...",
                    disabled=True,
                )

                extract_audio(url)

                filename: str = sanitize_filename(f"{title}.mp3")

                with open(f"cache/{filename}", "rb") as f:
                    placeholder.download_button(
                        "Download",
                        data=f,
                        file_name=filename,
                        mime="audio/mpeg",
                        on_click=on_download,
                    )
