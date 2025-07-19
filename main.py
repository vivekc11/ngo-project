from app import app # Import your Flask app instance

if __name__ == "__main__":
    # Runs the Flask development server
    app.run(host="0.0.0.0", port=5050, debug=True)

# The application will be accessible at http://127.0.0.1:5050