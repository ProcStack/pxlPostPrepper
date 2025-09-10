import os
import json
import requests
from dotenv import load_dotenv

# Load variables from .env
load_dotenv()


# === CONFIG ===
ACCESS_TOKEN = os.getenv("ACCESS_TOKEN")
INSTAGRAM_ACCOUNT_ID = os.getenv("INSTAGRAM_ACCOUNT_ID")  # the IG Business/account id
JSON_FILE = "projectDataStruct.json"
POSTED_DIR = "posted"

# Instagram Graph API base
GRAPH_API_URL = "https://graph.facebook.com/v21.0"


def load_json(path=JSON_FILE):
    if not os.path.exists(path):
        raise FileNotFoundError(f"JSON file not found: {path}")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def create_media_container(account_id, media):
    """
    Create a media container for a single image or video.
    Uses public URLs (media['URL']). The Graph API requires media to be reachable.

    Returns container id string on success, otherwise None.
    """
    if not media.get("URL"):
        print("Skipping media without public URL:", media.get("file_path"))
        return None

    url = f"{GRAPH_API_URL}/{account_id}/media"
    payload = {"access_token": ACCESS_TOKEN}

    mtype = media.get("type", "image").lower()
    if mtype == "image":
        payload["image_url"] = media["URL"]
    elif mtype == "video":
        payload["video_url"] = media["URL"]
    else:
        print("Unsupported media type:", mtype)
        return None

    # Per-child caption/description (note: Graph API historically prefers a single caption on the parent for carousels)
    if media.get("description"):
        payload["caption"] = media["description"]

    # Accessibility / alt text
    if media.get("alt_text"):
        # Graph API param name: accessibility_caption (some SDKs/versions accept 'accessibility_caption')
        payload["accessibility_caption"] = media["alt_text"]

    # User tags (Graph API expects user ids; here we pass a best-effort JSON string and note requirements)
    if media.get("user_tags"):
        # expected format: {"in": [{"user_id": "<id>", "x": 0.5, "y": 0.5}, ...]}
        # Caller currently may provide username; mapping to user_id is required before posting.
        try:
            payload["user_tags"] = json.dumps({"in": media["user_tags"]})
        except Exception:
            pass

    # Location id (if present)
    if media.get("location") and media["location"].get("id"):
        payload["location_id"] = media["location"]["id"]

    resp = requests.post(url, data=payload)
    result = resp.json()
    print("create_media_container ->", result)
    return result.get("id")


def create_carousel(account_id, post):
    """
    For carousels: create child containers first, then create a parent container with children list, then publish.
    """
    children = []
    for media in post.get("media", []):
        cid = create_media_container(account_id, media)
        if cid:
            children.append(cid)

    if not children:
        print("No valid children created for carousel")
        return None

    # Parent container
    create_url = f"{GRAPH_API_URL}/{account_id}/media"
    payload = {
        "access_token": ACCESS_TOKEN,
        "children": ",".join(children)
    }
    if post.get("caption"):
        payload["caption"] = post["caption"]

    resp = requests.post(create_url, data=payload)
    result = resp.json()
    print("create_carousel ->", result)
    return result.get("id")


def publish_container(account_id, creation_id):
    url = f"{GRAPH_API_URL}/{account_id}/media_publish"
    payload = {"creation_id": creation_id, "access_token": ACCESS_TOKEN}
    resp = requests.post(url, data=payload)
    print("publish_container ->", resp.json())
    return resp.json()


def process_post(post):
    kind = post.get("post_kind", post.get("type", "single")).lower()
    account_id = INSTAGRAM_ACCOUNT_ID
    if not account_id or not ACCESS_TOKEN:
        raise RuntimeError("Missing INSTAGRAM_ACCOUNT_ID or ACCESS_TOKEN in environment")

    if kind == "carousel":
        creation_id = create_carousel(account_id, post)
    elif kind in ("single", "image", "video"):
        # single media expected in media[0]
        media = post.get("media", [])
        if not media:
            print("No media found for single post")
            return None
        creation_id = create_media_container(account_id, media[0])
    else:
        print("Unsupported post kind:", kind)
        return None

    if not creation_id:
        print("No creation id obtained; aborting publish")
        return None

    return publish_container(account_id, creation_id)


def main():
    data = load_json()

    # minimal contract: data is a single post object OR a list of posts
    posts = data if isinstance(data, list) else [data]

    for post in posts:
        if post.get("posted"):
            continue

        print("Posting:", post.get("caption") or post.get("title") or "(no caption)")
        result = process_post(post)

        if result and result.get("id"):
            post["posted"] = True
            save_json(JSON_FILE, data)

            # Move local files if present (best-effort)
            os.makedirs(POSTED_DIR, exist_ok=True)
            for m in post.get("media", []):
                fp = m.get("file_path")
                if fp and os.path.exists(fp):
                    try:
                        dest = os.path.join(POSTED_DIR, os.path.basename(fp))
                        os.replace(fp, dest)
                    except Exception:
                        pass

            print("Post published, id=", result.get("id"))
        else:
            print("Failed to publish post:", result)


if __name__ == "__main__":
    main()
