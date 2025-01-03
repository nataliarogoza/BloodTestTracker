
## Description
**BloodTestTracker** is a Linux desktop application built using **Python**, **PyQt** and **PostgreSQL**. It is developed and tested on Linux Mint and is confirmed to work on Ubuntu 22.04.

With **BloodTestTracker** you can easily manage your blood test results over time. You can enter, update, or delete your results and visualize your data with statistics and plots of selected tests! The application automatically sets up a database to store your data during the initial setup.

## Installation and setup

### Before starting, make sure you have the following installed:

- **Python 3.10 (or later)** 
- **Git** 

#### Step 1: Clone the repository
``` 
git clone https://github.com/nataliarogoza/BloodTestTracker.git
cd BloodTestTracker
```

#### Step 2: Create the virtual environment 
To keep an app isolated from the global environment, it is best to run it from within a **virtual environment**. If Python's **venv** module is not installed, you can install it using the following commands:
```
sudo apt-get update
sudo apt-get install python3.10-venv
```
Once installed, create the virtual environment by running:
```
python3 -m venv venv
```
Then activate the virtual environment:
```
source venv/bin/activate  
```

#### Step 3: Configure setup
Make sure you're in ```BloodTestTracker/``` directory, then run the following command:
```
python3 app/setup.py 
```
This will prompt you to enter your PostgreSQL **username**, **password** and **database name**, where the table for storing blood test results will be created. The script will:  
- Create a ```.env``` file containing the provided database credentials. 
- Install PostgreSQL and set up the database
- Install all necessary Python packages listed in ```requirements.txt```.
**Warning: ```.env``` file stores your database credentials in plain text. Ensure you keep this file private and do not share it with others.**


#### Step 4: Run the desktop app:
```
python3 app/main.py
```

#### Step 5: Exit the virtual environment
When you are done, close the application and deactivate the virtual environment by running:
```
deactivate
```

## Files description

### ```BloodTestTracker/```

- ```.env.template```  

    Template file with placeholders for environment variables like database credentials. It is used to create the ```.env```file.

- ```requirements.txt```  

    A list of necessary Python packages that the application depends on, used for installing dependencies.

### ```BloodTestTracker/app/```:

- ```setup.py```  

    A setup script that prompts the user for PostgreSQL credentials, creates the ```.env``` file, initializes the database, and sets up the table for storing blood test results. It also installs Python packages listed in ```requirements.txt```.

- ```database.py```  

    Defines the ```DatabaseManager()``` class for managing database connections and queries, using the ```psycopg2``` library.

- ``` interface.py ```  

    Manages the GUI by handling the main application window, buttons, widgets, and other UI elements.

- ```main.py```  

    Initializes and launches application.

- ```custom.py```  

    Contains customizations for the ```QCalendarWidget()```, tailoring its appearance

- ```fonts/``` , ```images/```, ```resources/```  

    These directories contain supporting files (custom fonts, qss styles, icons, images, textfiles to display).

## Customizing 

### Adding new tests and units
The application does not yet allow for addition of new blood test types or units - they are predetermined. To add new types, update the ```test_names.txt``` and ```unit_names.txt``` files in the ```BloodTestTracker/app/resources/textfiles/```. Simply add the new names on separate lines in each respective file, then load the app again - they should be visible in adding results panel.

### Changing the background image
To change the background of the app, replace the ```background.png``` file with a new image of your choice.


## Other  
- The arrows used in the app’s widgets were custom-designed specifically for this project. 
- The ```axolotl.webp``` image used in the app was generated using OpenAI's DALL·E.
- This project uses the **Roboto Regular** font, licensed under the [Apache License 2.0](http://www.apache.org/licenses/LICENSE-2.0).  
- This is my first application. While it is not highly advanced, it is relatively complex and may contain errors or areas for improvement.

