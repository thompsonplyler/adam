# **Best Practices Guide: Flask, React, Zustand, & Mantine**

This document outlines the best practices for developing a real-time game using a tech stack composed of Flask, React, Zustand, Mantine, and PostgreSQL. The primary audience for this guide is an AI developer who will be implementing features and troubleshooting issues. The goal is to establish a consistent and high-quality development paradigm.

## **I. Philosophy & General Principles**

* **Separation of Concerns:** The frontend (React) and backend (Flask) should be developed and deployed as separate applications. This promotes modularity, scalability, and independent development cycles.  
* **API-First Design:** The backend should expose a well-defined RESTful API that the frontend consumes. This API should be documented (e.g., using Swagger/OpenAPI).  
* **Real-time Communication:** For the game's real-time features, WebSockets (via Flask-SocketIO) will be the primary communication protocol.  
* **Stateless Backend:** The Flask application should be as stateless as possible. Game state should be persisted in the PostgreSQL database, and session management can be handled via tokens (e.g., JWTs).  
* **Component-Based Architecture:** The React frontend should be built using a modular, component-based architecture.  
* **Centralized State Management:** Zustand will be used for managing global and complex local state in the React application.

## **II. Flask (Backend)**

### **A. Project Structure**

A well-organized Flask project is crucial for maintainability. A recommended structure is:  
/project  
|-- /app  
|   |-- \_\_init\_\_.py         \# App factory  
|   |-- /api                \# API blueprints  
|   |   |-- \_\_init\_\_.py  
|   |   |-- routes.py  
|   |-- /models             \# SQLAlchemy models  
|   |   |-- \_\_init\_\_.py  
|   |   |-- game.py  
|   |   |-- user.py  
|   |-- /services           \# Business logic  
|   |-- /socketio           \# Socket.IO event handlers  
|   |   |-- \_\_init\_\_.py  
|   |   |-- events.py  
|   |-- config.py           \# Configuration settings  
|-- /migrations         \# Database migrations  
|-- run.py              \# Application entry point  
|-- requirements.txt

### **B. Configuration**

* Use a config.py file to manage different environments (development, testing, production).  
* Store sensitive information (e.g., database credentials, secret keys) in environment variables, not in the code.

### **C. API Design**

* Use Flask Blueprints to organize your API into logical modules.  
* Adhere to RESTful principles: use appropriate HTTP verbs (GET, POST, PUT, DELETE), use status codes correctly, and have consistent URL naming conventions.  
* Implement versioning for your API (e.g., /api/v1/...).

### **D. Database (PostgreSQL with SQLAlchemy)**

* Use Flask-SQLAlchemy for seamless integration.  
* Define database models in separate files within the app/models directory.  
* Use Flask-Migrate (with Alembic) to manage database schema migrations.  
* Employ connection pooling to efficiently manage database connections.  
* For complex queries, consider using raw SQL when necessary for performance, but always sanitize inputs to prevent SQL injection.

### **E. Real-time with Flask-SocketIO**

* Organize Socket.IO event handlers in a dedicated socketio module.  
* Use namespaces to separate different real-time functionalities.  
* Use rooms for broadcasting messages to specific groups of clients (e.g., players in the same game instance).  
* Be mindful of the global context when handling events.

### **F. Authentication & Authorization**

* Use JSON Web Tokens (JWTs) for stateless authentication. Flask-JWT-Extended is a good choice.  
* Implement decorators for protecting routes and Socket.IO events that require authentication.

### **G. Testing**

* Write unit and integration tests using pytest.  
* Use a separate testing database.  
* Mock external services and dependencies where appropriate.

## **III. React (Frontend)**

### **A. Project Structure**

A feature-based project structure is recommended for scalability:  
/src  
|-- /api                \# API client (e.g., Axios instance)  
|-- /components         \# Reusable UI components  
|   |-- /common           \# Buttons, inputs, etc.  
|   |-- /layout           \# Page layout components  
|-- /features           \# Feature-specific components and logic  
|   |-- /game  
|   |   |-- /components  
|   |   |-- /hooks  
|   |   |-- /store  
|   |   |-- Game.jsx  
|-- /hooks              \# Global custom hooks  
|-- /lib                \# Third-party library configurations  
|-- /pages              \# Top-level page components  
|-- /store              \# Zustand store  
|-- /styles             \# Global styles  
|-- App.jsx  
|-- main.jsx

### **B. Component Design**

* Favor functional components with hooks.  
* Keep components small and focused on a single responsibility.  
* Use prop-types or TypeScript for type checking.

### **C. State Management with Zustand**

* Create a single store for global application state. For very large applications, consider creating separate stores for different domains.  
* Model actions as events, not as simple setters.  
* For performance, use selectors to subscribe to specific slices of the state. This prevents unnecessary re-renders.  
* Middleware (like devtools and persist) can be very useful for debugging and local storage synchronization.

### **D. Styling with Mantine**

* Leverage Mantine's theming capabilities to ensure a consistent look and feel. Create a custom theme file to define colors, typography, and other design tokens.  
* Use Mantine's component library as much as possible to maintain consistency and accessibility.  
* For custom styling, use the sx prop or create custom styles with createStyles.

### **E. API Communication**

* Use a dedicated API client (e.g., an Axios instance with base URL and interceptors) for all HTTP requests.  
* Handle API loading and error states gracefully in your components. Custom hooks can be useful for this.

### **F. Real-time with Socket.IO Client**

* Create a single Socket.IO client instance and share it across the application (e.g., through a React Context or a custom hook).  
* Handle Socket.IO events in a dedicated hook or service.  
* Update the Zustand store in response to Socket.IO events.

### **G. Testing**

* Use a testing library like React Testing Library for component testing.  
* Mock API calls and Socket.IO events to test components in isolation.

## **IV. Integration & Troubleshooting**

### **A. CORS**

* Enable Cross-Origin Resource Sharing (CORS) on the Flask backend using the Flask-CORS extension. Be sure to configure it correctly for your development and production environments.

### **B. Environment Variables**

* Use .env files for both the Flask and React applications to manage environment-specific variables.  
* In React, prefix environment variables with VITE\_ (for Vite) or REACT\_APP\_ (for Create React App).

### **C. Deployment**

* **Backend (Flask):** Deploy as a WSGI application using a production-ready server like Gunicorn or uWSGI, often behind a reverse proxy like Nginx.  
* **Frontend (React):** Build the React app into static files and serve them using a web server like Nginx or a CDN.  
* **Database (PostgreSQL):** Use a managed database service (e.g., Amazon RDS, Google Cloud SQL) for production.

### **D. Common Troubleshooting Scenarios**

* **Real-time updates not working:**  
  * Check for CORS issues.  
  * Verify that the Socket.IO client and server versions are compatible.  
  * Ensure that the event names match between the client and server.  
  * Check for any errors in the browser's developer console or the Flask server logs.  
* **State not updating correctly:**  
  * Use the Redux DevTools with Zustand's devtools middleware to inspect state changes.  
  * Ensure that you are not mutating the state directly.  
* **API requests failing:**  
  * Check the browser's network tab for details on the failed request.  
  * Verify that the API endpoint is correct and that the Flask server is running.  
  * Check for any authentication or authorization errors.

This document should serve as a living guide. As the project evolves, it should be updated to reflect new decisions and best practices.