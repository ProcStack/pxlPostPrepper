This project is a work-in-progress.
<br/>The steps below are only partially correct.
<br/>Since the auto-posting side still isn't working.

### Current Functionality

![pxlPostPrepper Window](_show/pxlPostPrepper_v0-0-1.webp)

 - Load Directories or multiple selected images to load as individual posts
 - Combine posts as needed
 - Add Comment, Alt Test, Live URL data per Post and Media
 - Save & Load your project as a JSON file to your computer
 - Mark `Has Posted` to colored a post Green
 - If you are randomly posting, like me, hit `Select Random Post` or `Select Random Un-Posted`

<br/>
<br/>
 - Find a Windows build in `Releases`
 - To run from Terminal / Command Prompt, you'll need PyQT6
 - Written in Python 3.10.6


### Pyinstaller
If you feel like building the exe, using `pyinstaller` -
<br/>`pyinstaller --onefile --windowed --icon=Icon.ico --add-data="Icon.ico;."  pxlPostPrepper.py`


### Work-In-Progress
I'm leaving the info below for when the auto-posting scripts work

XXX

What you'll need for this to work -
<br/> - An Intagram account set to 'Professional'; your pro. account can be Creative or Business
<br/>&nbsp;&nbsp; | Simply set your Personal account to Professional for free from your account settings in instagram.
<br/> - Create a [Meta App for Instagram](https://developers.facebook.com/docs/instagram-platform/create-an-instagram-app)
<br/> - Get your developer & app credentials
<br/> - Rename or duplicate `.env_base` to `.env`
<br/> - In the `.env` update the entries with your credentials.
<br/> - Right click in the browser folder for `pxlAutoPoster` and click `Open in Terminal`
<br/> - Double-click `setup.bat` -or- run `pip install requirements.txt` from the repo's root.
<br/> - You should now be ready to double click the `pxlAutoPoster.py` file, or run `python pxlAutoPoster.py`

<br/>
<br/> In the tool, make new posts in the right side bar, select items for the post from the left bar, altering any scaling or image cropping as needed.

When Saving, your posts will be saved to the location you set in the `.env` file.
<br/>In the future, I'll set it up to read multiple accounts, but for now, I only need this automated for one account.
<br/>So that's what you'll get too haha.