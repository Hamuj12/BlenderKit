#!/usr/bin/env python3
"""Standalone BlenderKit HDRI downloader.

Before running, export your API key:
    export BLENDERKIT_API_KEY=your_token_here

Example usage:
    python download_asset.py --id 35a48631-49a4-4265-9fe0-843f5e936b53

Optionally specify a resolution (e.g. --resolution resolution_8K) or a custom
output directory (e.g. --output ./my_downloads).
"""

import argparse
import os
import sys
import uuid
from pathlib import Path
from typing import Dict, Optional
from urllib.parse import urlparse

import requests

DEFAULT_SERVER = os.getenv("BLENDERKIT_SERVER", "https://www.blenderkit.com").rstrip("/")
API_ROOT = f"{DEFAULT_SERVER}/api/v1"
DEFAULT_OUTPUT_DIR = "downloads"
DEFAULT_RESOLUTION = "resolution_4K"
USER_AGENT = "BlenderKitStandaloneDownloader/1.0"
REQUEST_TIMEOUT = 30
STREAM_TIMEOUT = 60


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Download a BlenderKit HDRI by asset_base_id.")
    parser.add_argument("--id", dest="asset_base_id", required=True, help="Asset base ID to download.")
    parser.add_argument(
        "--resolution",
        default=DEFAULT_RESOLUTION,
        help=(
            "Preferred fileType to download (e.g. resolution_8K). "
            "If unavailable, the script falls back to the highest available resolution."
        ),
    )
    parser.add_argument(
        "--output",
        default=DEFAULT_OUTPUT_DIR,
        help="Directory where the HDRI will be saved (default: ./downloads).",
    )
    parser.add_argument(
        "--scene",
        default=None,
        help="Optional scene UUID to report to the API. Defaults to a random UUID4.",
    )
    return parser.parse_args()


def read_api_key() -> str:
    api_key = os.getenv("BLENDERKIT_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError(
            "Missing API key. Export BLENDERKIT_API_KEY before running this script."
        )
    return api_key


def build_headers(api_key: str, accept_json: bool = True) -> Dict[str, str]:
    headers: Dict[str, str] = {"User-Agent": USER_AGENT}
    if accept_json:
        headers["Accept"] = "application/json"
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    return headers


def fetch_asset_metadata(asset_base_id: str, api_key: str) -> Dict:
    params = {"query": f"asset_base_id:{asset_base_id}", "dict_parameters": "1"}
    response = requests.get(
        f"{API_ROOT}/search/",
        params=params,
        headers=build_headers(api_key),
        timeout=REQUEST_TIMEOUT,
    )
    response.raise_for_status()
    payload = response.json()
    results = payload.get("results", [])
    if not results:
        raise RuntimeError(f"No asset found for asset_base_id={asset_base_id}.")
    return results[0]


def resolution_value(file_type: str) -> float:
    if not file_type.lower().startswith("resolution_"):
        return 0.0
    suffix = file_type.split("resolution_", 1)[1]
    suffix = suffix.replace("_", ".")
    if suffix.upper().endswith("K"):
        try:
            return float(suffix[:-1]) * 1024
        except ValueError:
            return 0.0
    try:
        return float(suffix)
    except ValueError:
        return 0.0


def select_file_entry(asset_data: Dict, preferred_type: Optional[str]) -> Dict:
    files = asset_data.get("files", [])
    if not files:
        raise RuntimeError("Asset metadata does not contain downloadable files.")

    if preferred_type:
        for entry in files:
            if entry.get("fileType", "").lower() == preferred_type.lower():
                return entry

    resolution_files = [f for f in files if f.get("fileType", "").lower().startswith("resolution_")]
    if resolution_files:
        resolution_files.sort(key=lambda f: resolution_value(f.get("fileType", "")), reverse=True)
        return resolution_files[0]

    for entry in files:
        if entry.get("fileType") == "blend":
            return entry

    return files[0]


def request_signed_url(download_url: str, api_key: str, scene_uuid: str) -> str:
    response = requests.get(
        download_url,
        headers=build_headers(api_key),
        params={"scene_uuid": scene_uuid} if scene_uuid else None,
        timeout=REQUEST_TIMEOUT,
    )
    response.raise_for_status()
    data = response.json()
    file_path = data.get("filePath") or data.get("filepath")
    if not file_path:
        raise RuntimeError("Download endpoint did not return a filePath.")
    return file_path


def download_file(url: str, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    with requests.get(url, stream=True, headers={"User-Agent": USER_AGENT}, timeout=STREAM_TIMEOUT) as response:
        response.raise_for_status()
        with destination.open("wb") as handle:
            for chunk in response.iter_content(chunk_size=1024 * 256):
                if chunk:
                    handle.write(chunk)


def derive_filename(file_entry: Dict, download_url: str) -> str:
    server_path = file_entry.get("filename") or ""
    name = os.path.basename(server_path)
    if not name:
        name = os.path.basename(urlparse(download_url).path)
    return name or "downloaded_asset"


def main() -> None:
    args = parse_args()
    try:
        api_key = read_api_key()
        asset = fetch_asset_metadata(args.asset_base_id, api_key)
        if asset.get("assetType", "").upper() != "HDR":
            print(
                f"Warning: asset {args.asset_base_id} is of type {asset.get('assetType')} (expected HDR).",
                file=sys.stderr,
            )

        file_entry = select_file_entry(asset, args.resolution)
        scene_uuid = args.scene or str(uuid.uuid4())
        signed_url = request_signed_url(file_entry["downloadUrl"], api_key, scene_uuid)
        filename = derive_filename(file_entry, signed_url)

        target_dir = Path(args.output).expanduser().resolve() / asset.get("assetBaseId", asset.get("id", "asset"))
        destination = target_dir / filename

        print(f"Downloading {asset.get('name')} -> {destination}")
        download_file(signed_url, destination)
        print("Download complete.")
    except requests.HTTPError as http_err:
        print(f"HTTP error: {http_err}", file=sys.stderr)
        sys.exit(1)
    except Exception as err:
        print(f"Error: {err}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
