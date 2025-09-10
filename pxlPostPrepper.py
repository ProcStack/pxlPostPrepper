import sys
import os
import json
from datetime import datetime
from functools import partial
import random
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QLineEdit, QComboBox, QFileDialog, QTextEdit, QCheckBox,
    QScrollArea, QSizePolicy, QDateTimeEdit, QListWidget, QListWidgetItem, QInputDialog, QSplitter
)
from PyQt6.QtGui import QPixmap, QIcon
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QMessageBox

pxlPostPrepperVersion = "0.0.1"

def resource_path(relative_path):
    # When running from a PyInstaller bundle, data files are unpacked to _MEIPASS
    if getattr(sys, "frozen", False):
        base = sys._MEIPASS
    else:
        base = os.path.dirname(__file__)
    return os.path.join(base, relative_path)

class pxlPostPrepper(QWidget):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Social Media Prepping Tool :: pxlPostPrepper v" + pxlPostPrepperVersion)
        self.setGeometry(100, 100, 1000, 600)
        icon_path = resource_path("Icon.ico")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))

        self.active_preview_filepath = ""

        # Main layout
        main_v = QVBoxLayout(self)

        # Top area: left sidebar, preview, right file list
        # we'll use a QSplitter for the top area so columns are user-resizable

        # Left Sidebar
        sidebar = QVBoxLayout()
        sidebar.addWidget(QLabel("Access Token"))
        self.access_token = QLineEdit('---')
        sidebar.addWidget(self.access_token)
        self.access_token.setDisabled(True)

        sidebar.addWidget(QLabel("Instagram Account ID"))
        self.ig_account_id = QLineEdit('---')
        sidebar.addWidget(self.ig_account_id)
        self.ig_account_id.setDisabled(True)

        save_env_btn = QPushButton("Save .env")
        sidebar.addWidget(save_env_btn)
        save_env_btn.setDisabled(True)

        #sideBarSpacer = QWidget()
        #sideBarSpacer.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding)
        #sidebar.addWidget(sideBarSpacer)

        select_random_post_btn = QPushButton("Select Random Post")
        sidebar.addWidget(select_random_post_btn)
        select_random_post_btn.clicked.connect(self._select_random_post)

        select_random_unposted_btn = QPushButton("Select Random Un-Posted")
        sidebar.addWidget(select_random_unposted_btn)
        select_random_unposted_btn.clicked.connect(self._select_random_unposted)

        # Post count label (will be updated by refresh_post_bar)
        self.post_count_label = QLabel('Total Post Count : 0')
        sidebar.addWidget(self.post_count_label)

        # Post bar (moved from bottom to left sidebar) - vertical list of posts
        self.post_bar_area = QScrollArea()
        self.post_bar_area.setWidgetResizable(True)
        
        # prefer expanding vertically but fixed horizontally
        self.post_bar_area.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        bar_container = QWidget()
        # ensure the internal container has a reasonable minimum width but may expand
        # Use minimum width rather than fixed so buttons can stretch horizontally when space is available
        bar_container.setMinimumWidth(180)
        bar_container.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.post_bar_layout = QVBoxLayout(bar_container)
        self.post_bar_layout.setContentsMargins(0, 0, 0, 0)
        self.post_bar_layout.setSpacing(4)
        self.post_bar_area.setWidget(bar_container)

        sidebar.addWidget(self.post_bar_area)

        # sidebar layout is ready; we'll wrap it into a widget later for the splitter

        # Media details sidebar (per-media alt / live URL)
        self.media_details_scroll = QScrollArea()
        self.media_details_scroll.setWidgetResizable(True)
        media_details_container = QWidget()
        self.media_details_layout = QVBoxLayout(media_details_container)
        self.media_details_layout.setContentsMargins(6, 6, 6, 6)
        self.media_details_layout.setSpacing(8)
        self.media_details_scroll.setWidget(media_details_container)
        self.media_details_scroll.setMinimumWidth(260)
        # allow the media details area to expand when layout gives it space
        self.media_details_scroll.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        # At the top of the media details pane, add post-level metadata editors
        self.meta_container = QWidget()
        meta_layout = QVBoxLayout(self.meta_container)
        meta_layout.setContentsMargins(0, 0, 0, 0)
        meta_layout.setSpacing(6)

        meta_layout.addWidget(QLabel('Post Name'))
        self.post_name_edit = QLineEdit()
        meta_layout.addWidget(self.post_name_edit)

        meta_layout.addWidget(QLabel('Keywords (comma separated)'))
        self.keywords_edit = QLineEdit()
        meta_layout.addWidget(self.keywords_edit)

        # posted checkbox to indicate if this post has already gone live
        self.posted_checkbox = QCheckBox('Has posted')
        meta_layout.addWidget(self.posted_checkbox)

        meta_layout.addWidget(QLabel('Date Modified'))
        self.date_modified_label = QLabel('')
        self.date_modified_label.setStyleSheet('color: gray;')
        meta_layout.addWidget(self.date_modified_label)

        # Move crop, caption, scheduled time, and stats into meta layout
        #meta_layout.addWidget(QLabel("Crop Type"))
        #self.crop_type = QComboBox()
        #self.crop_type.addItems(["Original", "1:1", "4:5", "16:9", "9:16"])
        #meta_layout.addWidget(self.crop_type)

        meta_layout.addWidget(QLabel("Caption"))
        self.caption_edit = QTextEdit()
        self.caption_edit.setFixedHeight(80)
        meta_layout.addWidget(self.caption_edit)

        #meta_layout.addWidget(QLabel("Scheduled Time (optional)"))
        #self.scheduled = QDateTimeEdit()
        #self.scheduled.setCalendarPopup(True)
        #meta_layout.addWidget(self.scheduled)

        # Stats display
        self.stats_label = QLabel("Resolution: - \nAspect Ratio: -")
        meta_layout.addWidget(self.stats_label)

        self.media_details_layout.addWidget(self.meta_container)
        # Per-post media container (isolated area for thumbnails and per-media controls)
        # This keeps media widgets separate so we can clear them without touching
        # other controls like merge buttons and post-level metadata.
        self.per_post_media_container = QWidget()
        self.per_post_media_layout = QVBoxLayout(self.per_post_media_container)
        self.per_post_media_layout.setContentsMargins(0, 0, 0, 0)
        self.per_post_media_layout.setSpacing(6)
        self.media_details_layout.addWidget(self.per_post_media_container)

        # bottom spacer (will push merge button to the bottom)
        self.meta_bottom_spacer = QWidget()
        self.meta_bottom_spacer.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding)
        self.media_details_layout.addWidget(self.meta_bottom_spacer)

        # Merge Previous button: move selected media to the previous post then delete this post
        # place merge buttons together
        merge_btn_row = QWidget()
        merge_btn_row_l = QHBoxLayout(merge_btn_row)
        merge_btn_row_l.setContentsMargins(0, 0, 0, 0)
        self.merge_left_btn = QPushButton('Merge Previous')
        merge_btn_row_l.addWidget(self.merge_left_btn)
        self.merge_left_btn.clicked.connect(self._merge_left)

        # Merge Into... button - prompts for which post to merge into
        self.merge_into_btn = QPushButton('Merge Into...')
        merge_btn_row_l.addWidget(self.merge_into_btn)
        self.merge_into_btn.clicked.connect(self._merge_into_prompt)

        # keep a reference to the whole row so refresh_media_details can preserve it
        self.merge_btn_row = merge_btn_row
        self.media_details_layout.addWidget(self.merge_btn_row)

        # create center and right wrappers later and put everything into a QSplitter

        # wire metadata edits
        self.post_name_edit.textChanged.connect(partial(self._update_post_meta, 'post_name'))
        self.keywords_edit.textChanged.connect(partial(self._update_post_meta, 'keywords'))
        self.posted_checkbox.toggled.connect(lambda s: self._update_post_meta('has_posted', bool(s)))
        # keep caption in sync with the currently loaded post
        self.caption_edit.textChanged.connect(self._on_caption_changed)

        # Center preview + media bar
        center_container = QVBoxLayout()

        self.preview = QLabel("Drop an image here")
        self.preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview.setStyleSheet("border: 2px dashed #aaa;")
        self.preview.setMinimumSize(500, 400)
        # keep the original pixmap so we can rescale to available space on demand
        self.current_pixmap_orig = None
        self.preview.setScaledContents(False)
        center_container.addWidget(self.preview, 1)

        imgDetails_hlayout = QHBoxLayout()
        self.preview_filename = QLabel("File name")
        self.preview_filename.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview_filename.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        imgDetails_hlayout.addWidget(self.preview_filename)

        copy_imagePath_btn = QPushButton("Copy Image Path")
        imgDetails_hlayout.addWidget(copy_imagePath_btn)
        copy_imagePath_btn.clicked.connect(lambda: QApplication.clipboard().setText(self.active_preview_filepath))

        copy_imageData_btn = QPushButton("Copy Image Data")
        imgDetails_hlayout.addWidget(copy_imageData_btn)
        copy_imageData_btn.clicked.connect(self.copy_image_data)

        center_container.addLayout(imgDetails_hlayout)

        # Note: media bar removed; thumbnails are shown in the media details pane as clickable buttons

        # center container added to a wrapper later for the splitter

        # Right files list
        right_v = QVBoxLayout()
        # import button on right
        self.import_btn = QPushButton("Import images from directory")
        right_v.addWidget(self.import_btn)
        self.import_btn.clicked.connect(self.import_from_directory)

        # Load image button (legacy single file loader)
        load_btn = QPushButton("Load Image(s)")
        right_v.addWidget(load_btn)
        load_btn.clicked.connect(self.load_image)

        # load posts from JSON
        self.load_posts_btn = QPushButton("Load posts from JSON")
        right_v.addWidget(self.load_posts_btn)
        self.load_posts_btn.clicked.connect(self.load_posts_from_json)

        right_v.addWidget(QLabel("Imported files"))
        self.files_list = QListWidget()
        right_v.addWidget(self.files_list)

        # new post from selected file
        self.new_post_btn = QPushButton("New post from selected")
        right_v.addWidget(self.new_post_btn)
        self.new_post_btn.clicked.connect(self.new_post_from_selected)

        # add selected file to currently edited post
        self.add_to_post_btn = QPushButton("Add to current post")
        right_v.addWidget(self.add_to_post_btn)
        self.add_to_post_btn.clicked.connect(self.add_selected_to_post)

        # Delete & Save buttons
        self.delete_post_btn = QPushButton("Delete post")
        right_v.addWidget(self.delete_post_btn)
        self.delete_post_btn.clicked.connect(self.delete_current_post)

        self.save_all_btn = QPushButton("Save all posts to JSON")
        right_v.addWidget(self.save_all_btn)
        self.save_all_btn.clicked.connect(self.save_all_posts)

        # Build a QSplitter with the four column widgets so the user can resize panes
        left_widget = QWidget()
        left_widget.setLayout(sidebar)

        media_widget = QWidget()
        media_layout_wrapper = QVBoxLayout(media_widget)
        media_layout_wrapper.setContentsMargins(0, 0, 0, 0)
        media_layout_wrapper.addWidget(self.media_details_scroll)

        center_widget = QWidget()
        center_widget.setLayout(center_container)

        right_widget = QWidget()
        right_widget.setLayout(right_v)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(left_widget)
        splitter.addWidget(media_widget)
        splitter.addWidget(center_widget)
        splitter.addWidget(right_widget)

        # set sensible initial sizes (pixels). Adjust these if you want different proportions.
        splitter.setSizes([200, 300, 600, 200])

        main_v.addWidget(splitter)

        # Current post label - keep it a single-line height and avoid vertical stretching
        self.current_post_label = QLabel("No post selected")
        # expand horizontally but keep a fixed vertical size that matches the text
        self.current_post_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        # set a fixed height based on the widget's size hint so it doesn't stretch vertically
        try:
            h = self.current_post_label.sizeHint().height()
            self.current_post_label.setFixedHeight(h)
        except Exception:
            # fallback: set a small reasonable fixed height
            self.current_post_label.setFixedHeight(24)
        # vertically center the label text within its fixed height
        try:
            self.current_post_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        except Exception:
            self.current_post_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
        main_v.addWidget(self.current_post_label)

        self.setLayout(main_v)

        # Model
        self.posts = []  # list of post dicts
        self.current_index = None
        self.imported_files = []
        self.selected_media_index = None

        # Initialize UI
        self.refresh_post_bar()

        # wire file list click
        self.files_list.itemClicked.connect(self.on_file_clicked)

    def load_image(self):
        file_names, _ = QFileDialog.getOpenFileNames(self, "Open Image", "", "Images (*.png *.jpg *.jpeg *.mp4)")
        if file_names:
            for file_name in file_names:
                self._load_preview(file_name)
                # create a post for this single file
                post = self._make_post_from_file(file_name)
                self.posts.append(post)
            self.current_index = len(self.posts) - 1
            self.load_post(self.current_index)
            self.refresh_post_bar()

    def _load_preview(self, file_path):
        if file_path.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.gif')):
            pixmapOrig = QPixmap(file_path)
            # store original so we can rescale when the widget size changes
            self.current_pixmap_orig = pixmapOrig
            # scale to available preview size (with a sensible default cap applied)
            try:
                self._update_preview_scaled()
            except Exception:
                # fallback to a safe default size
                pixmap = pixmapOrig.scaled(600, 400, Qt.AspectRatioMode.KeepAspectRatio)
                self.preview.setPixmap(pixmap)
            # show original resolution in stats
            self.stats_label.setText(f"Resolution: {pixmapOrig.width()}x{pixmapOrig.height()}\nAspect Ratio: {pixmapOrig.width()/pixmapOrig.height():.2f}")
        else:
            self.preview.setText(os.path.basename(file_path))
            self.current_pixmap_orig = None
        delimiter = "/" if "/" in file_path else "\\"
        filename_dispArr = file_path.split(delimiter)
        filename_dispStr = delimiter.join(filename_dispArr[-3::])
        self.preview_filename.setText(filename_dispStr)
        self.active_preview_filepath = file_path

    def _update_preview_scaled(self):
        """Scale the stored original pixmap to fit the preview widget, capped at 1080x1350.

        Keeps aspect ratio and uses smooth transformation.
        """
        if not getattr(self, 'current_pixmap_orig', None):
            return
        orig = self.current_pixmap_orig
        # available space in the preview widget
        avail_w = max(1, self.preview.width())
        avail_h = max(1, self.preview.height())
        # cap to Instagram-like maximum (1080x1350)
        cap_w = 1080
        cap_h = 1350
        target_w = min(avail_w, cap_w)
        target_h = min(avail_h, cap_h)
        # scale preserving aspect ratio
        scaled = orig.scaled(target_w, target_h, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
        self.preview.setPixmap(scaled)

    def copy_image_data(self):
        """Copy the current image to the clipboard."""
        if not getattr(self, 'current_pixmap_orig', None):
            return
        clipboard = QApplication.clipboard()
        clipboard.setPixmap(self.current_pixmap_orig)

    def resizeEvent(self, event):
        # update preview scaling when the window is resized
        try:
            self._update_preview_scaled()
        except Exception:
            pass
        try:
            super().resizeEvent(event)
        except Exception:
            return

    def _make_post_from_file(self, file_path):
        _, ext = os.path.splitext(file_path)
        mtype = 'video' if ext.lower() in ['.mp4', '.mov', '.webm'] else 'image'
        media = {
            "file_path": file_path.replace('\\', '/'),
            "URL": None,
            "type": mtype,
            "description": "",
            "alt_text": "",
            "user_tags": [],
            "location": {"id": None, "name": None}
        }
        post = {
            "post_kind": "single",
            "caption": "",
            "media": [media],
            "scheduled_time": None,
            "post_options": {"allow_comments": True, "disable_reshare": False, "audience": "PUBLIC", "share_to_fb": False}
        }
        # local metadata for organizing posts in the project
        post['local_data'] = {
            'post_name': '',
            'date_modified': datetime.now().replace(microsecond=0).isoformat(),
            'keywords': []
        }
        return post

    def new_post_from_selected(self):
        selected_items = self.files_list.selectedItems()
        if not selected_items:
            return
        for item in selected_items:
            file_path = item.data(Qt.ItemDataRole.UserRole)
            post = self._make_post_from_file(file_path)
            self.posts.append(post)
        self.refresh_post_bar()
    
    def add_selected_to_post(self):
        selected_items = self.files_list.selectedItems()
        if not selected_items:
            return
        # If there's a current post, add media items to it. Otherwise, create new posts.
        if self.current_index is None:
            for item in selected_items:
                file_path = item.data(Qt.ItemDataRole.UserRole)
                post = self._make_post_from_file(file_path)
                self.posts.append(post)
            # select the first of the newly added posts
            self.current_index = len(self.posts) - len(selected_items)
            self.load_post(self.current_index)
        else:
            cur = self.posts[self.current_index]
            for item in selected_items:
                file_path = item.data(Qt.ItemDataRole.UserRole)
                media = self._make_post_from_file(file_path)['media'][0]
                cur.setdefault('media', []).append(media)
            # mark the post as modified when media are added
            self._touch_post_modified()
            # refresh the loaded post display
            self.load_post(self.current_index)
        self.refresh_post_bar()

    def _on_thumbnail_clicked(self, path, idx):
        # load preview and set selected index
        self._load_preview(path)
        self.selected_media_index = idx
        # update the media details pane selection
        self.refresh_media_details()

    def refresh_media_details(self):
        # Clear only the per-post media layout. This keeps post-level editors and
        # merge controls intact.
        try:
            while self.per_post_media_layout.count():
                it = self.per_post_media_layout.takeAt(0)
                if it is None:
                    continue
                w = it.widget()
                if w:
                    w.setParent(None)
        except Exception:
            pass

        if self.current_index is None:
            return

        post = self.posts[self.current_index]
        media = post.get('media', [])
        for i, m in enumerate(media):
            row = QWidget()
            row_l = QHBoxLayout(row)
            row_l.setContentsMargins(0, 0, 0, 0)


            # controls: move left, delete, move right
            controls_v = QVBoxLayout()
            controls_v.setContentsMargins(5, 0, 5, 0)
            controls_post_options = QVBoxLayout()
            controls_post_options.setContentsMargins(0, 0, 0, 0)
            prev_btn = QPushButton('▲')
            prev_btn.setFixedWidth(28)
            prev_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            prev_btn.clicked.connect(partial(self._move_media, i, i-1))
            del_btn = QPushButton('⛌')
            del_btn.setFixedWidth(28)
            del_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            del_btn.clicked.connect(partial(self._delete_media, i))
            next_btn = QPushButton('▼')
            next_btn.setFixedWidth(28)
            next_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            next_btn.clicked.connect(partial(self._move_media, i, i+1))
            controls_post_options.addWidget(prev_btn)
            controls_post_options.addWidget(del_btn)
            controls_post_options.addWidget(next_btn)
            controls_v.addLayout(controls_post_options)
            row_l.addLayout(controls_v)
            


            # small thumb
            fp = m.get('file_path')
            if fp and os.path.exists(fp) and fp.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.gif')):
                # use a clickable button with the image as an icon so thumbnails are only
                # shown in the media details pane and are clickable to change the preview
                px = QPixmap(fp).scaled(100, 100, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                thumb_btn = QPushButton()
                thumb_btn.setIcon(QIcon(px))
                thumb_btn.setIconSize(px.size())
                thumb_btn.setFixedSize(px.width()+6, px.height()+6)
                # show pointer cursor on hover to indicate clickability
                try:
                    thumb_btn.setCursor(Qt.CursorShape.PointingHandCursor)
                except Exception:
                    # fallback for different PyQt versions
                    try:
                        thumb_btn.setCursor(Qt.PointingHandCursor)
                    except Exception:
                        pass
                # capture fp and index in lambda
                thumb_btn.clicked.connect(lambda checked, path=fp, idx=i: self._on_thumbnail_clicked(path, idx))
                row_l.addWidget(thumb_btn)
            else:
                row_l.addWidget(QLabel(os.path.basename(fp) if fp else ''))

            field_v = QVBoxLayout()

            filename_str = os.path.basename(fp) if fp else ''
            filename_text = QLabel(filename_str)
            field_v.addWidget(filename_text)

            alt_edit = QLineEdit(m.get('alt_text') or '')
            alt_edit.setPlaceholderText('Alt text')
            alt_edit.textChanged.connect(lambda text, idx=i: self._update_media_field(idx, 'alt_text', text))
            field_v.addWidget(alt_edit)

            url_edit = QLineEdit(m.get('URL') or '')
            url_edit.setPlaceholderText('Live URL')
            url_edit.textChanged.connect(lambda text, idx=i: self._update_media_field(idx, 'URL', text))
            field_v.addWidget(url_edit)

            row_l.addLayout(field_v)

            # add to the per-post media layout
            try:
                self.per_post_media_layout.addWidget(row)
            except Exception:
                self.media_details_layout.addWidget(row)

    def _update_media_field(self, index, key, value):
        # Update the media field in the model and touch modified time
        if self.current_index is None:
            return
        try:
            media = self.posts[self.current_index]['media'][index]
        except Exception:
            return
        media[key] = value
        self._touch_post_modified()
        
    def _merge_into_prompt(self):
        """Show a dialog letting the user pick which post to merge the current post into."""
        if self.current_index is None:
            return
        if not self.posts or len(self.posts) < 2:
            return

        # Build a list of display names for all posts except the current one.
        choices = []
        index_map = []
        for i, p in enumerate(self.posts):
            if i == self.current_index:
                continue
            local = p.get('local_data', {}) or {}
            name = local.get('post_name') or ''
            title = name if name else f"Post {i+1}"
            choices.append(f"{i+1} : {title}")
            index_map.append(i)

        if not choices:
            return

        item, ok = QInputDialog.getItem(self, "Merge Into", "Select target post to merge into:", choices, 0, False)
        if not ok or not item:
            return

        # map selected display item back to the actual post index
        sel_idx = choices.index(item)
        target_idx = index_map[sel_idx]
        self._merge_into(target_idx)

    def _merge_into(self, target_idx: int):
        """Merge selected media (or all) from current post into the specified target post index."""
        if self.current_index is None:
            return
        if target_idx is None or target_idx < 0 or target_idx >= len(self.posts):
            return
        cur_idx = self.current_index
        if cur_idx == target_idx:
            return

        cur_post = self.posts[cur_idx]
        target_post = self.posts[target_idx]

        cur_media = cur_post.get('media', [])
        if not cur_media:
            return

        # Decide which media to move: selected index if present, otherwise move all
        if self.selected_media_index is not None and 0 <= self.selected_media_index < len(cur_media):
            items_to_move = [cur_media.pop(self.selected_media_index)]
        else:
            items_to_move = cur_media[:]  # copy all
            cur_post['media'] = []

        # append to target post's media list
        target_post.setdefault('media', []).extend(items_to_move)

        # touch modified times on target
        try:
            if 'local_data' not in target_post:
                target_post['local_data'] = {}
            target_post['local_data']['date_modified'] = datetime.utcnow().replace(microsecond=0).isoformat()
        except Exception:
            pass

        # remove the current post and adjust target index if needed
        try:
            del self.posts[cur_idx]
        except Exception:
            pass

        # if the deleted post was before the target, the target index shifts left by 1
        if cur_idx < target_idx:
            target_idx -= 1

        # set current index to the target and refresh UI
        self.current_index = max(0, target_idx)
        self.refresh_post_bar()
        self.load_post(self.current_index)
        try:
            self._touch_post_modified()
        except Exception:
            pass

    def _update_post_meta(self, key, value):
        # Called by UI editors (post_name, keywords) to update post-level metadata
        if self.current_index is None:
            return
        post = self.posts[self.current_index]
        if 'local_data' not in post:
            post['local_data'] = {}
        post['local_data'][key] = value
        self._touch_post_modified()
        # update post bar labels so names show immediately
        try:
            self.refresh_post_bar()
        except Exception:
            pass

    def _delete_media(self, index):
        if self.current_index is None:
            return
        post = self.posts[self.current_index]
        media = post.get('media', [])
        # Prompt user for confirmation before deleting media
        reply = QMessageBox.question(
            self,
            "Delete Media",
            "Are you sure you want to remove this image from the post?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        if 0 <= index < len(media):
            del media[index]
            # adjust selected_media_index
            if self.selected_media_index is not None:
                if self.selected_media_index >= len(media):
                    self.selected_media_index = max(0, len(media) - 1) if media else None
            self._touch_post_modified()
            self.refresh_media_details()

    def _move_media(self, old_idx, new_idx):
        if self.current_index is None:
            return
        post = self.posts[self.current_index]
        media = post.get('media', [])
        if not (0 <= old_idx < len(media)):
            return
        # clamp new index
        new_idx = max(0, min(new_idx, len(media)-1))
        if new_idx == old_idx:
            return
        item = media.pop(old_idx)
        media.insert(new_idx, item)
        # update selection index to moved item
        self.selected_media_index = new_idx
        self._touch_post_modified()
        self.refresh_media_details()

    def _touch_post_modified(self):
        # Update the post's local_data.date_modified and the UI label
        if self.current_index is None:
            return
        post = self.posts[self.current_index]
        if 'local_data' not in post:
            post['local_data'] = {}
        now = datetime.utcnow().replace(microsecond=0).isoformat()
        post['local_data']['date_modified'] = now
        try:
            self.date_modified_label.setText(now)
        except Exception:
            pass

    def _on_caption_changed(self):
        """Called when the caption editor changes; update model and UI."""
        if self.current_index is None:
            return
        try:
            cur = self.posts[self.current_index]
            cur['caption'] = self.caption_edit.toPlainText()
            # mark modified and refresh post bar so short preview updates
            self._touch_post_modified()
            try:
                self.refresh_post_bar()
            except Exception:
                pass
        except Exception:
            pass

    def _update_media_field(self, index, key, value):
        if self.current_index is None:
            return
        post = self.posts[self.current_index]
        media = post.setdefault('media', [])
        if 0 <= index < len(media):
            media[index][key] = value

    def on_file_clicked(self, item):
        file_path = item.data(Qt.ItemDataRole.UserRole)
        if file_path:
            self._load_preview(file_path)

    def import_from_directory(self):
        dir_path = QFileDialog.getExistingDirectory(self, "Select image directory")
        if not dir_path:
            return
        added = 0
        for fname in sorted(os.listdir(dir_path)):
            if fname.lower().endswith(('.png', '.jpg', '.jpeg', '.mp4', '.mov', '.webm')):
                full = os.path.join(dir_path, fname)
                # add to the right-hand files list (avoid duplicates)
                if full not in self.imported_files:
                    item = QListWidgetItem(os.path.basename(full))
                    item.setData(Qt.ItemDataRole.UserRole, full)
                    self.files_list.addItem(item)
                    self.imported_files.append(full)
                post = self._make_post_from_file(full)
                self.posts.append(post)
                added += 1
        if added:
            self.current_index = len(self.posts) - added
            self.load_post(self.current_index)
            self.refresh_post_bar()

    def load_posts_from_json(self):
        fn, _ = QFileDialog.getOpenFileName(self, 'Load posts from JSON', '', 'JSON Files (*.json)')
        if not fn:
            return
        try:
            with open(fn, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except Exception as e:
            print('Failed to load posts:', e)
            return

        # Expect data to be a list of post-like dicts
        posts = []
        # clear current files list
        self.files_list.clear()
        self.imported_files = []

        for p in data:
            # preserve and normalize local_data
            local = p.get('local_data', {}) or {}
            # ensure has_posted is carried into local_data whether it's top-level or inside local_data
            local['has_posted'] = bool(p.get('has_posted', local.get('has_posted', False)))
            # normalize keywords to list
            kws = local.get('keywords', [])
            if isinstance(kws, str):
                kws = [k.strip() for k in kws.split(',') if k.strip()]
            if kws is None:
                kws = []
            local.setdefault('post_name', '')
            local.setdefault('date_modified', datetime.now().replace(microsecond=0).isoformat())
            local['keywords'] = kws

            post = {
                'post_kind': p.get('post_kind', 'single'),
                'caption': p.get('caption', ''),
                'media': [],
                'scheduled_time': p.get('scheduled_time'),
                'post_options': p.get('post_options', {}),
                'local_data': local
            }
            for m in p.get('media', []) or []:
                # prefer file_path, fall back to URL
                fp = m.get('file_path') or m.get('file') or m.get('URL')
                # add to files_list for quick access (avoid duplicates)
                if fp and fp not in self.imported_files:
                    item = QListWidgetItem(os.path.basename(fp))
                    item.setData(Qt.ItemDataRole.UserRole, fp)
                    self.files_list.addItem(item)
                    self.imported_files.append(fp)

                media_entry = {
                    'file_path': fp,
                    'URL': m.get('URL'),
                    'type': m.get('type', 'image'),
                    'description': m.get('description', ''),
                    'alt_text': m.get('alt_text', ''),
                    'user_tags': m.get('user_tags', []),
                    'location': m.get('location', {'id': None, 'name': None})
                }
                post['media'].append(media_entry)
            posts.append(post)

        self.posts = posts
        if self.posts:
            self.current_index = 0
            self.load_post(0)
        self.refresh_post_bar()

    def refresh_post_bar(self):
        # remember horizontal scroll position so rebuilding doesn't jump
        try:
            hbar = self.post_bar_area.horizontalScrollBar()
            prev_scroll = hbar.value()
        except Exception:
            hbar = None
            prev_scroll = 0

        # update the total post count label if present
        try:
            if hasattr(self, 'post_count_label'):
                self.post_count_label.setText(f'Total Post Count : {len(self.posts)}')
        except Exception:
            pass

        # clear existing buttons
        while self.post_bar_layout.count():
            item = self.post_bar_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.setParent(None)

        for idx, post in enumerate(self.posts):
            local = post.get('local_data', {}) or {}
            name = local.get('post_name') or ''
            if name:
                title = name
            else:
                title = f"Post {idx+1}"
            btn = QPushButton(f"{idx+1} : {title}")
            try:
                btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            except Exception:
                pass
            try:
                btn.setAutoDefault(False)
                btn.setDefault(False)
            except Exception:
                pass
            btn.setFixedHeight(40)
            btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            btn.clicked.connect(lambda checked, i=idx: self.load_post(i))

            # Determine background color based on selection and posted state
            is_selected = (self.current_index == idx)
            posted = bool(local.get('has_posted'))
            if is_selected and posted:
                btn.setStyleSheet('background-color: #96b596; color: black; font-weight: bold;')
            elif is_selected:
                btn.setStyleSheet('background-color: #707070; font-weight: bold;')
            elif posted:
                btn.setStyleSheet('background-color: #6eac6f; color: black;')
            else:
                # Default
                btn.setStyleSheet('')
            self.post_bar_layout.addWidget(btn)

        # spacer to push items left
        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self.post_bar_layout.addWidget(spacer)

        # restore previous scroll location if possible
        try:
            if hbar is not None:
                # clamp to maximum to avoid exceptions
                hbar.setValue(min(prev_scroll, hbar.maximum()))
        except Exception:
            pass

    def _select_random_post(self):
        """Select a random post and load it into the editor."""
        try:
            if not getattr(self, 'posts', None):
                return
            idx = random.randrange(len(self.posts))
            self.load_post(idx)
            # ensure UI reflects selection
            try:
                self.refresh_post_bar()
            except Exception:
                pass
        except Exception:
            return

    def _select_random_unposted(self):
        """Select a random unposted post and load it into the editor."""
        try:
            if not getattr(self, 'posts', None):
                return
            unposted_indices = [i for i, post in enumerate(self.posts) if not post.get('local_data', {}).get('has_posted')]
            if not unposted_indices:
                return
            idx = random.choice(unposted_indices)
            self.load_post(idx)
            # ensure UI reflects selection
            try:
                self.refresh_post_bar()
            except Exception:
                pass
        except Exception:
            return

    def load_post(self, index):
        if index is None or index < 0 or index >= len(self.posts):
            return
        self.current_index = index
        post = self.posts[index]
        # populate post-level metadata editors
        local = post.get('local_data', {})
        self.post_name_edit.setText(local.get('post_name') or '')
        kws = local.get('keywords') or []
        if isinstance(kws, list):
            self.keywords_edit.setText(','.join(kws))
        else:
            self.keywords_edit.setText(str(kws))
        self.date_modified_label.setText(local.get('date_modified') or '')
        # update posted checkbox to reflect this post's state
        try:
            self.posted_checkbox.setChecked(bool(local.get('has_posted')))
        except Exception:
            pass
        self.caption_edit.setPlainText(post.get('caption') or '')
        media = post.get('media', [])
        if media:
            m = media[0]
            fp = m.get('file_path')
            if fp and os.path.exists(fp):
                self._load_preview(fp)
            # refresh the media details pane
            self.selected_media_index = 0
            self.refresh_media_details()
        """
        sched = post.get('scheduled_time')
        if sched:
            try:
                dt = datetime.fromisoformat(sched)
                self.scheduled.setDateTime(dt)
            except Exception:
                pass
        """
        # update posted checkbox to reflect this post's state (do after details refresh)
        try:
            if hasattr(self, 'posted_checkbox'):
                self.posted_checkbox.setChecked(bool(local.get('has_posted')))
        except Exception:
            pass
        # enable/disable merge left depending on whether there is a previous post
        try:
            # Merge left: only enabled when there's a previous post
            if hasattr(self, 'merge_left_btn'):
                self.merge_left_btn.setEnabled(self.current_index is not None and self.current_index > 0)
                try:
                    self.merge_left_btn.setText(f"Merge {self.current_index + 1} > {self.current_index}")
                except Exception:
                    pass
            # Merge into: enabled when there is at least one other post
            if hasattr(self, 'merge_into_btn'):
                has_other = len(self.posts) > 1 and self.current_index is not None
                self.merge_into_btn.setEnabled(has_other)
        except Exception:
            pass
        # update current post label to show index and post name
        try:
            local = post.get('local_data', {}) or {}
            pname = local.get('post_name') or ''
            display = f"Post {index+1} : {pname}" if pname else f"Post {index+1}"
            if hasattr(self, 'current_post_label'):
                self.current_post_label.setText(display)
        except Exception:
            pass
    

    def delete_current_post(self):
        if self.current_index is None:
            return
        try:
            del self.posts[self.current_index]
        except Exception:
            return
        # adjust current index
        if not self.posts:
            self.current_index = None
            self.preview.setText('Drop an image here')
            self.preview_filename.setText('-- Load an image --')
            self.active_preview_filepath = ""
            self.caption_edit.clear()
            # clear media details
            self.selected_media_index = None
            self.refresh_media_details()
            # update current post label when no posts remain
            try:
                if hasattr(self, 'current_post_label'):
                    self.current_post_label.setText('No post selected')
            except Exception:
                pass
        else:
            self.current_index = max(0, self.current_index - 1)
            self.load_post(self.current_index)
            self.refresh_media_details()
        self.refresh_post_bar()

    def save_all_posts(self):
        if not self.posts:
            return
        # update current post from editor fields
        if self.current_index is not None:
            cur = self.posts[self.current_index]
            cur['caption'] = self.caption_edit.toPlainText()
            """
            dt = self.scheduled.dateTime()
            if dt:
                try:
                    iso = dt.toString(Qt.DateFormat.ISODate)
                    cur['scheduled_time'] = iso
                except Exception:
                    cur['scheduled_time'] = None
            """
        # Ask where to save
        fn, _ = QFileDialog.getSaveFileName(self, 'Save posts to JSON', 'projectDataStruct.json', 'JSON Files (*.json)')
        if not fn:
            return
        # convert posts to array of projectDataStruct-like objects
        out = []
        for p in self.posts:
            # ensure shape
            copy = {
                'post_kind': p.get('post_kind', 'single'),
                'caption': p.get('caption', ''),
                'media': p.get('media', []),
                'scheduled_time': p.get('scheduled_time'),
                'post_options': p.get('post_options', {})
            }
            # include project-local metadata if present
            if 'local_data' in p:
                copy['local_data'] = p['local_data']
            out.append(copy)

        try:
            with open(fn, 'w', encoding='utf-8') as f:
                json.dump(out, f, indent=2)
            print('Saved posts to', fn)
        except Exception as e:
            print('Failed to save posts:', e)
    
    def _merge_left(self):
        # Move selected media (or all media if none selected) from current post into previous post and delete current post
        if self.current_index is None:
            return
        if self.current_index == 0:
            return
        cur_idx = self.current_index
        prev_idx = cur_idx - 1
        cur_post = self.posts[cur_idx]
        prev_post = self.posts[prev_idx]

        cur_media = cur_post.get('media', [])
        if not cur_media:
            # nothing to merge
            return

        # Decide which media to move: selected index if present, otherwise move all
        if self.selected_media_index is not None and 0 <= self.selected_media_index < len(cur_media):
            items_to_move = [cur_media.pop(self.selected_media_index)]
        else:
            items_to_move = cur_media[:]  # copy
            cur_post['media'] = []

        # append to previous post's media list
        prev_post.setdefault('media', []).extend(items_to_move)

        # touch modified times
        try:
            if 'local_data' not in prev_post:
                prev_post['local_data'] = {}
            prev_post['local_data']['date_modified'] = datetime.utcnow().replace(microsecond=0).isoformat()
        except Exception:
            pass

        # delete current post
        try:
            del self.posts[cur_idx]
        except Exception:
            pass

        # set current index to previous post and refresh UI
        self.current_index = prev_idx
        self.refresh_post_bar()
        self.load_post(self.current_index)
        # touch modified time on the loaded (previous) post
        try:
            self._touch_post_modified()
        except Exception:
            pass


if __name__ == "__main__":
    app = QApplication(sys.argv)

    icon_path = resource_path("Icon.ico")
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))

    window = pxlPostPrepper()
    window.show()

    sys.exit(app.exec())

