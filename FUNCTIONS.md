# BlenderKit Asset Search, Metadata, and Download Functions

Below is a catalog of Python functions involved in searching assets, fetching metadata, generating download URLs, downloading files, and handling authentication within the BlenderKit add-on code base. Line numbers are 1-indexed.

## client_lib.py
- **ensure_minimal_data(data: Optional[dict] = None)** (line 71)
  - Ensures outbound payloads include the current API key, process ID, platform, and add-on version before calling the BlenderKit client. Returns the enriched `dict`.
  - Adds authentication metadata consumed by every `/blender/*` and `/wrappers/*` call.
- **ensure_minimal_data_class(data_class)** (line 94)
  - Injects API key, process ID, platform, and add-on version into dataclass-based payloads such as `SearchData`. Returns the updated object for client communication.
- **asset_search(search_data: datas.SearchData)** (line 177)
  - Submits a search request to the local client by POSTing JSON to `/blender/asset_search`. Returns the JSON response containing a task handle.
- **asset_download(data)** (line 192)
  - Starts an asset download task through the client by POSTing payload data (including preferences and download dirs) to `/blender/asset_download`. Returns task metadata as JSON.
- **cancel_download(task_id: str)** (line 201)
  - Sends a GET request to `/blender/cancel_download` with the task ID to abort an in-flight download task. Returns the raw `requests.Response`.
- **download_gravatar_image(author_data: datas.UserProfile)** (line 228)
  - Fetches or caches author avatar imagery by GETting `/profiles/download_gravatar_image`. Useful for metadata enrichment of authors shown with assets.
- **get_user_profile()** (line 242)
  - Initiates retrieval of the logged-in user profile from `/profiles/get_user_profile`. Returns a `requests.Response` for the created client task.
- **get_download_url(asset_data, scene_id, api_key)** (line 387)
  - Calls the blocking wrapper `/wrappers/get_download_url` to resolve whether an asset can be downloaded and to obtain the signed download URL and filename. Returns `(can_download, download_url, filename)`.
- **blocking_file_download(url: str, filepath: str, api_key: str)** (line 437)
  - Uses the `/wrappers/blocking_file_download` wrapper to synchronously download a file via the client, storing it at `filepath`. Returns the `requests.Response` from the client.
- **blocking_request(url: str, method: str = "GET", headers: Optional[dict] = None, json_data: Optional[dict] = None, timeout: tuple = TIMEOUT)** (line 453)
  - Issues a blocking HTTP call through the client via `/wrappers/blocking_request`, mirroring the given HTTP verb, headers, and JSON body. Returns the proxied response.
- **nonblocking_request(url: str, method: str, headers: Optional[dict] = None, json_data: Optional[dict] = None, messages: Optional[dict] = None)** (line 480)
  - Schedules a non-blocking HTTP request through `/wrappers/nonblocking_request`, returning immediately while the client performs the call. Useful for background metadata updates.
- **send_oauth_verification_data(code_verifier, state: str)** (line 514)
  - Posts PKCE verification values to `/oauth2/verification_data` so the client can complete OAuth callbacks. Returns the client response.
- **refresh_token(refresh_token, old_api_key)** (line 534)
  - Requests a refreshed API token by GETting `/refresh_token` through the client, passing the stored refresh token. Returns the `requests.Response`.
- **oauth2_logout()** (line 551)
  - Sends a GET request to `/oauth2/logout` to revoke the current OAuth tokens and unsubscribe the add-on instance.

## search.py
- **parse_result(r)** (line 180)
  - Normalizes and enriches raw search results (asset metadata), preparing thumbnail names, available resolutions, author data, and cached download URLs.
- **handle_search_task(task: client_tasks.Task)** (line 333)
  - Processes completed search tasks, parsing each asset result via `parse_result`, preloading thumbnails, and updating UI state.
- **add_search_process(query, get_next: bool, page_size: int, next_url: str, history_id: str)** (line 918)
  - Builds the search URL and posts a `SearchData` payload to `client_lib.asset_search`, registering the resulting task for follow-up.
- **get_search_simple(parameters, filepath=None, page_size=100, max_results=100000000, api_key="")** (line 950)
  - Performs a blocking REST query against `BLENDERKIT_API/search/`, optionally paging through all results. Uses `client_lib.blocking_request` and can export results to disk.
- **search(get_next=False, query=None, author_id="")** (line 1002)
  - Central orchestration for initiating searches from UI filters. Validates state, builds queries, and delegates to `add_search_process`.
- **get_search_results() -> list[dict]** (line 1864)
  - Retrieves the current list of parsed search results from the active history step for downstream features (e.g., progress overlays).

## download.py
- **update_asset_metadata(asset_main, asset_data)** (line 648)
  - Writes downloaded metadata (IDs, tags, description, serialized asset data) onto the appended Blender datablock for later reuse.
- **handle_download_task(task: client_tasks.Task)** (line 827)
  - Reacts to client download task updates, forwarding errors and invoking `download_post` when a download finishes.
- **download_post(task: client_tasks.Task)** (line 878)
  - Runs after download completion: updates stored file paths and URLs, copies files if needed, and triggers append/link workflows.
- **download(asset_data, **kwargs)** (line 962)
  - Prepares the download payload (preferences, resolution, download directories) and calls `client_lib.asset_download`, storing the task handle.
- **check_downloading(asset_data, **kwargs) -> bool** (line 1001)
  - Detects if an asset is already downloading; if so, attaches new drag targets and avoids duplicate requests.
- **check_existing(asset_data, resolution="blend", can_return_others=False)** (line 1024)
  - Resolves expected file paths via `paths.get_download_filepaths`, verifies presence on disk, and synchronizes copies between global/local caches.
- **download_write_progress(task_id, task)** (line 859)
  - Updates stored task progress and search-result download percentages based on client progress reports.
- **start_download(asset_data, **kwargs) -> bool** (line 1231)
  - Entry point for starting downloads: checks for existing instances, duplicates assets if already in scene, otherwise calls `download`.
- **clear_downloads()** (line 853)
  - Clears the internal download task registry, effectively cancelling tracking for in-progress downloads.

## bg_utils.py
- **download_asset_file(asset_data, resolution="blend", api_key="")** (line 34)
  - Background-friendly helper that resolves target file paths, checks existing files, and performs a synchronous download via `client_lib.blocking_file_download`.

## paths.py
- **get_download_dirs(asset_type)** (line 144)
  - Computes global/local directories where a given asset type should be stored, honoring add-on preferences and OS constraints.
- **get_res_file(asset_data, resolution, find_closest_with_url=False)** (line 261)
  - Selects the best matching file entry for a requested resolution, falling back to closest available or original blend/zip file. Returns `(file_entry, resolved_resolution)`.
- **get_download_filepaths(asset_data, resolution="blend", can_return_others=False)** (line 348)
  - Builds absolute file paths for the selected asset file across all configured download directories, creating folders as needed.
- **server_to_local_filename(server_filename: str, asset_name: str) -> str** (line 309)
  - Converts server-side filenames (e.g., `resolution_4K_uuid.blend`) into user-friendly local filenames prefixed with the asset slug.

## utils.py
- **api_key_property_updated(user_preferences, context)** (line 550)
  - Validates API key length, triggers profile fetch and search refresh on success, or resets the key and reports an error if invalid.
- **get_headers(api_key: str = "") -> dict[str, str]** (line 963)
  - Produces HTTP headers for direct API calls, including platform and add-on version, and adds an `Authorization` bearer token when supplied.

## bkit_oauth.py
- **handle_login_task(task: client_tasks.Task)** (line 41)
  - Processes OAuth login task results, writing new tokens on success or logging out on failure.
- **handle_logout_task(task: client_tasks.Task)** (line 86)
  - Responds to `/oauth2/logout` task results by displaying status messages and clearing stored credentials.
- **logout() -> None** (line 112)
  - Calls `client_lib.oauth2_logout()` and purges stored API credentials from preferences.
- **login(signup: bool)** (line 119)
  - Initiates the OAuth flow by opening the BlenderKit authorization URL in a browser, sending PKCE data via `client_lib.send_oauth_verification_data`.
- **write_tokens(auth_token, refresh_token, oauth_response)** (line 153)
  - Persists newly issued access and refresh tokens, updating the add-on preferences and extension repository configuration.
- **ensure_token_refresh() -> bool** (line 169)
  - Checks token expiry and, when close to timeout, triggers `client_lib.refresh_token` to obtain a new API key.

## asset_bar_op.py
- **handle_bkclientjs_get_asset(task: search.client_tasks.Task)** (line 2304)
  - Handles assets shared from the web gallery by parsing provided metadata, seeding search history with the asset, and opening the asset bar UI.

## Additional Search/Download Utilities
- **FUNCTIONS ABOVE** integrate with the BlenderKit client endpoints such as `/blender/asset_search`, `/blender/asset_download`, `/wrappers/get_download_url`, `/wrappers/blocking_file_download`, and `/oauth2/*`, enabling end-to-end asset discovery, metadata retrieval, and authenticated downloads.
