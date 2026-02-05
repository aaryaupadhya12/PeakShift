# "Helping hands" software
## 📋 Project Description

At retail stores, management staff offer to work in the stores during very busy times like weekends and holidays. This is an app which faciliitates this initiative

## 🧑‍💻 Development Team (TRM)

- [@aaryaupadhya12](https://github.com/pes1ug23am006-dot) 
- [@Anshullmudyavar1](https://github.com/Anshullmudyavar1) 
- [@aaravadarsh18](https://github.com/aaravadarsh18) 
- [@AHaveeshKumar](https://github.com/AHaveeshKumar) 



## 🚀 Getting Started

### Prerequisites
- Python 3.11.0
- Node.js 24.11.0

### Installation
2. Install dependencies
   ```bash
   pip install -r requiremnts.txt
   cd src/frontend npm init 
   ```

3. Run the application
   ```bash
   python run.py(in root directory)

   In new terminal 
   cd src/frontend 
   npm start 
   ```

## 📁 Project Structure

```
PESU_RR_AIML_A_P19_Helping_hands_software_TRM/
├── src/                 # Source code
├── docs/               # Documentation
├── tests/              # Test files
├── .github/            # GitHub workflows and templates
├── README.md          # This file
└── ...
```

## 🛠️ Development Guidelines

### Branching Strategy
- `main`: Production-ready code
- `develop`: Development branch
- `feature/*`: Feature branches
- `bugfix/*`: Bug fix branches

### Commit Messages
Follow conventional commit format:
- `feat:` New features
- `fix:` Bug fixes
- `docs:` Documentation changes
- `style:` Code style changes
- `refactor:` Code refactoring
- `test:` Test-related changes

### Code Review Process
1. Create feature branch from `develop`
2. Make changes and commit
3. Create Pull Request to `develop`
4. Request review from team members
5. Merge after approval

## 📚 Documentation

- [API Documentation](docs/api.md)
- [User Guide](docs/user-guide.md)
- [Developer Guide](docs/developer-guide.md)

## 🧪 Testing

```bash
# Run tests
npm test

# Run tests with coverage
npm run test:coverage
```

##  Shift Notifications (New)

This release adds server-side email notifications when a new shift is published.

How it works:
- When a shift status is changed to "published" via POST /api/shifts/{id}/publish, the backend will send an email to all staff (users with role `manager` or `admin`).
- The email includes shift details and a direct link to the frontend where volunteers can sign up.

Configuration (environment variables):
- SENDGRID_API_KEY: SendGrid API key for sending emails (optional for local development).
- FROM_EMAIL: Sender email address (defaults to no-reply@example.com).
- FRONTEND_URL: Base URL for frontend app (defaults to http://localhost:3000).

Note: For development without SendGrid, the server will print the email content to stdout instead of sending.
