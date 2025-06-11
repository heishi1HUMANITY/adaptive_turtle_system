# Frontend Application

This project was bootstrapped with [Create React App](https://github.com/facebook/create-react-app).

## Purpose

The frontend application provides the user interface (UI) for interacting with the system. It allows users to view data, input information, and trigger actions that are processed by the backend. Its primary goal is to offer an intuitive and responsive user experience.

## Key Features and User Flows

This section outlines the main features available in the frontend and the typical user interactions associated with them.

- **Feature 1**: [Description of Feature 1]
  - *User Flow*: [Step-by-step user interaction for Feature 1]
- **Feature 2**: [Description of Feature 2]
  - *User Flow*: [Step-by-step user interaction for Feature 2]
*(Further features and flows will be documented here as they are identified or developed).*

## Communication with Backend API

The frontend application communicates with the backend API to fetch data, send updates, and trigger operations. Key aspects of this communication include:

*   **API Requests:** Uses HTTP/S requests (GET, POST, PUT, DELETE) to interact with specific backend endpoints.
*   **Data Exchange:** Typically sends and receives data in JSON format.
*   **Backend Dependency:** The backend server (usually at `http://localhost:8000`) must be running for the frontend to be fully functional. The frontend checks the backend's status via its `/api/health` endpoint.
*   **Error Handling:** Implements mechanisms to handle API errors gracefully and provide feedback to the user.

## Available Scripts

In the project directory, you can run:

### 1. Install Dependencies

```bash
npm install
```
Installs the necessary dependencies for the application. You should run this command first after cloning the repository or when dependencies need to be updated.

### 2. Start the Development Server

To run the app in development mode:
```bash
bash start_frontend.sh
```
Alternatively, if you have made the script executable (`chmod +x start_frontend.sh`):
```bash
./start_frontend.sh
```
This will start the development server, and you can open [http://localhost:3000](http://localhost:3000) to view it in your browser.

The page will reload automatically when you make changes to the code.
You may also see any lint errors in the console.

*(The `start_frontend.sh` script simply runs `npm start` but provides a consistent way to start applications across this project).*

### Running on Windows (PowerShell)
If you are on Windows, you can use the PowerShell script from within the `frontend` directory:
```powershell
.\start_frontend.ps1
```
Ensure your execution policy allows running local scripts (e.g., by running `Set-ExecutionPolicy RemoteSigned -Scope Process` in PowerShell). This script also runs `npm start`.

## Common Troubleshooting Tips

*   **Application Not Loading:**
    *   Ensure all dependencies are installed using `npm install`.
    *   Check if another application is using port 3000.
    *   Look for errors in the browser's developer console.
*   **Data Not Appearing or Stale Data:**
    *   Verify the backend server is running and accessible.
    *   Check the browser's developer console for API request errors (e.g., network errors, 4xx/5xx status codes).
    *   Ensure the backend API endpoints being called are correct and functioning as expected.
*   **`npm start` Fails:**
    *   Check for error messages in the console. Common issues include missing dependencies or conflicts.
    *   Ensure Node.js and npm are installed correctly and are of compatible versions.
    *   Try deleting the `node_modules` directory and `package-lock.json` (or `yarn.lock`) and then run `npm install` again.
    *   Ensure the `start_frontend.sh` script has execute permissions (`chmod +x start_frontend.sh`) or that `start_frontend.ps1` can be run if on Windows.
*   **Lint Errors in Console:**
    *   These are usually code style or potential error warnings. Address them as reported by the linter.
