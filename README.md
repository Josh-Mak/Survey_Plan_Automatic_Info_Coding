# Survey_Plan_Automatic_Info_Coding
A program which automatically records information from survey plans onto a .csv using AI.

**Important Notes**:
  1. In order for the program to work, it needs an OpenAI API key with access to both gpt-4-vision-preview and gpt-4-1106-preview.
  2. The program uses poppler for pdf to image conversions. **Poppler 23.11.0** must be extracted to the working directory.
    - Get poppler here: https://github.com/oschwartz10612/poppler-windows/releases/
    - A newer version of poppler could be used, all that needs to change is the poppler_path argument on line 59 and 69 of main.py.

**Intro**: This program is a quickly made prototype for a land survey company to help automatically code information from survey plans onto a .csv file. It served as a great introduction to using the OpenAI API and produts in development for me.

**Technical Overview**: This program relies heavily on AI from OpenAI to analyze the plans. Here's a breakdown of how it works:
  1. The program takes all of the files uploaded by the user and transforms them to .png's or .jpg's if they are not already in image format.
  2. Using OpenCV (cv2) the user can select regions of interest on the images so that only the relevant information is stored.
  3. The cropped images are passed into the gpt-4-vision API, which returns plain text for all of the text in the image.
  4. The text is passed to the gpt-4 API (LLM), which uses a one-shot prompt to return a JSON with the relevant information about the plan.
  5. The JSON is converted to a .csv and saved for the user.

**Future Improvements**: As stated earlier this is a simple prototype, and the main challenge for future improvement comes in accuracy. Currently the program is ~80% accurate. It *should* be able to reach ~99% accuracy with increased examples for the AI to pull from and checking answers against databases for things like township/municipality. Getting it to 100% accuracy will be the real challenge. Other than that there are a few needed improvements:
  - The #1 thing that this program needs and that I would do next is to add a simple UI to let the user know what is going on behind the scenes. Right now without explicit instructions it simply does not give you enough information to know what to do.  
  - The program would benefit from more user control about what stages of the program happen when. For example, giving the user an option to upload files and crop out the regions of interest, but not run the analysis until a later time.
