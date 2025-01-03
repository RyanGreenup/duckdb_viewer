# Features to Implement

## Required Features
## Nice Fetures

- Allow the user to create plots from the data
    - Select the columns to plot
    - Select the type of plot
- Create new tables with a form
- Paginate the Table for large tables


### Plotting
- [x] Hover Details
- [ ] Add a legend
- Create a double ended slider to limit the x and y-axis
- [x] Labels for x-axis and y-axis combo boxes are reversed from the combo boxes.
- The plots should have a slider to control how much data
    - Just take a sample (without replacement) of size max(N, n)
- [ ] Rotate x-axis 45 degrees
    - Make a bit of a gap at the bottom

## Features being implemented

- Execute SQL Tab
    - Edit environment
    - Popups for tables, fields, views and basic commands.
    - [x] Display errors in a text region
- Context Menu
    - Right click to drop a table or view
    - Create a new Table
    - Edit a Table


## DONE

## General
- Filter columns with string
- Show full db structure including tables, views, columns etc.
    - Ensure it remains connected to the table
- Display the column type in the header
- Highlight the SQL code with pygments
- Menu bar
    - Allow opening a new database

## Table

- Drag to make table wider
- Double click to set column width
- Horizontal scroll should be impleemented in the Execute SQL Tab
    - Make this a part of the Table view widget
### Filtering

- Fix filtering
    - When the user begins filtering, the horizontal scroll is lost and the table is not displayed correctly.
- Get Schema to clipboard command
    - Keybidning
- User should be able to filter in the Execute SQL tab
