# 🗄️ Google Drive Backup Tool

A simple, secure, and open-source tool to download all your Google Drive files as organized ZIP archives. No technical setup required - just authenticate with Google and download!

![Drive Backup Tool](https://img.shields.io/badge/Google%20Drive-Backup%20Tool-blue?style=flat&logo=googledrive)
![Python](https://img.shields.io/badge/Python-3.8+-green?style=flat&logo=python)
![FastAPI](https://img.shields.io/badge/FastAPI-Framework-red?style=flat&logo=fastapi)

## ✨ Features

- 🔐 **Secure OAuth 2.0** - No passwords stored, uses Google's official authentication
- 📁 **Complete Backup** - Downloads ALL file types including Google Docs, Sheets, Slides
- 🗜️ **Smart Organization** - Automatically creates ZIP files (2GB max each)
- ⚡ **Real-time Progress** - Live progress tracking with file counts and status
- 🔄 **Smart Export** - Converts Google Workspace files to standard formats:
  - Google Docs → Microsoft Word (.docx)
  - Google Sheets → Microsoft Excel (.xlsx)
  - Google Slides → Microsoft PowerPoint (.pptx)
  - Google Drawings → PDF (.pdf)
- 💾 **Memory Efficient** - Streams large files without using excessive RAM
- 🌐 **Web Interface** - Beautiful, responsive UI that works on any device
- 🛡️ **Privacy First** - All processing happens locally, nothing stored on external servers

## 🚀 Quick Start

### Prerequisites
- Python 3.8 or higher
- Google account with Drive data to backup

### 1. Clone and Setup
```bash
git clone <repository-url>
cd google-drive-backup
make setup
```

### 2. Get Google OAuth Credentials
1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing one
3. Enable the **Google Drive API**
4. Create OAuth 2.0 credentials (Web application type)
5. Add redirect URI: `http://localhost:8000/auth/callback`
6. Download the credentials

### 3. Configure Environment
Edit `.env` file with your Google OAuth credentials:
```bash
GOOGLE_CLIENT_ID=your_client_id_here
GOOGLE_CLIENT_SECRET=your_client_secret_here
REDIRECT_URL=http://localhost:8000/auth/callback
```

### 4. Run the Service
```bash
make run-stable
```

### 5. Start Backup
1. Open `http://localhost:8000` in your browser
2. Click **"Sign in with Google"**
3. Authorize the application
4. Click **"Start Complete Backup"**
5. Watch the progress and download your ZIP files!

## 📋 Available Commands

```bash
make setup       # Complete setup from scratch
make run         # Development server with auto-reload
make run-stable  # Stable server (recommended for backups)
make prod        # Production server with multiple workers
make clean       # Clean up downloads and cache
make help        # Show all available commands
```

## 📁 File Organization

Your backups are saved to:
```
downloads/
  └── [unique-session-id]/
      ├── drive_backup_001.zip
      ├── drive_backup_002.zip
      └── drive_backup_003.zip
```

Each backup session gets its own folder with sequentially numbered ZIP files.

## 🔧 Configuration Options

### Environment Variables
| Variable | Description | Default |
|----------|-------------|---------|
| `GOOGLE_CLIENT_ID` | Your Google OAuth client ID | Required |
| `GOOGLE_CLIENT_SECRET` | Your Google OAuth client secret | Required |
| `REDIRECT_URL` | OAuth redirect URI | `http://localhost:8000/auth/callback` |

### Customization
You can modify these settings in `app.py`:
- **Max ZIP size**: Currently 2GB per file
- **File filters**: Currently excludes folders and non-downloadable files
- **Export formats**: Customize Google Workspace export formats

## 🛠️ Technical Details

### Architecture
- **Backend**: FastAPI (Python) with Google APIs
- **Frontend**: Pure HTML/CSS/JavaScript (no framework dependencies)
- **Authentication**: OAuth 2.0 with Google
- **File Processing**: Streaming downloads with ZIP compression

### Security
- OAuth 2.0 flow with state validation
- Session-based authentication
- No credentials stored permanently
- Files processed locally only
- Automatic session cleanup

### Performance
- Streams large files to minimize memory usage
- Background processing for downloads
- Automatic ZIP file rotation at 2GB
- Efficient pagination for large Drive accounts

## 🔍 Troubleshooting

### Common Issues

**"OAuth error" or authentication fails**
- Verify your Google OAuth credentials in `.env`
- Ensure redirect URI matches exactly: `http://localhost:8000/auth/callback`
- Check that Google Drive API is enabled in your Google Cloud project

**"Session not found" errors**
- Clear browser cookies and try again
- Restart the server with `make run-stable`

**Large files timing out**
- The service automatically handles large files by streaming
- Google Workspace files >10MB may fail due to Google's export limits

**Server keeps reloading**
- Use `make run-stable` instead of `make run`
- This disables auto-reload for more stable operation

**Port 8000 already in use**
```bash
sudo lsof -ti:8000 | xargs kill -9
make run-stable
```

### Getting Help
1. Check the console output for detailed error messages
2. Verify your `.env` file has correct credentials
3. Try clearing browser cookies and restarting the server
4. For Google-specific issues, check the [Google Drive API documentation](https://developers.google.com/drive/api)

## 🚀 Production Deployment

### Docker
```bash
make docker-build
make docker-run
```

### Manual Production
1. **Use HTTPS**: Update redirect URI to use `https://yourdomain.com/auth/callback`
2. **Environment Variables**: Set credentials as environment variables instead of `.env`
3. **Domain Verification**: Verify your domain in Google Cloud Console
4. **Run Production Server**:
   ```bash
   make prod
   ```

### Security Considerations
- Always use HTTPS in production
- Consider additional rate limiting
- Monitor Google API quotas
- Implement proper logging and monitoring
- Set up automatic cleanup of old backup files

## 🤝 Contributing

This is an open-source project! Contributions are welcome:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests: `make test`
5. Format code: `make format`
6. Submit a pull request

### Development Setup
```bash
make dev-install  # Install development dependencies
make format      # Format code with black
make lint        # Run linting
make test        # Run tests
```

## 📄 License

This project is open source and available under the [MIT License](LICENSE).

## 🙏 Acknowledgments

- Built with [FastAPI](https://fastapi.tiangolo.com/)
- Uses [Google APIs Python Client](https://github.com/googleapis/google-api-python-client)
- Inspired by tools like [rclone](https://rclone.org/) but simplified for non-technical users

## ⚠️ Disclaimer

This tool is provided as-is for personal use. Always verify your backups and ensure you comply with Google's Terms of Service. The developers are not responsible for any data loss or account issues.

---

**Made with ❤️ for the open source community**

*Need help? Found a bug? Have a feature request? Please open an issue!*
