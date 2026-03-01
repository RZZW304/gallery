# Gallery - Photo Album Website Specification

## Project Overview
- **Project Name**: Gallery
- **Type**: Full-stack web application (Flask + React)
- **Core Functionality**: Photo album publishing platform with admin panel and user ratings
- **Target Users**: Photo enthusiasts, photographers, casual users sharing albums
- **Port**: localhost:21523

## Color Palette
```
--lime-cream: #d9ed92ff;
--light-green: #b5e48cff;
--light-green-2: #99d98cff;
--emerald: #76c893ff;
--ocean-mist: #52b69aff;
--tropical-teal: #34a0a4ff;
--bondi-blue: #168aadff;
--cerulean: #1a759fff;
--baltic-blue: #1e6091ff;
--yale-blue: #184e77ff;
```

## UI/UX Specification

### Visual Style
- **Era**: 2015-style (pre-material design, slightly dated but clean)
- **Not**: Neon, super modern, flat design
- **Aesthetic**: Warm, inviting, slightly retro but functional
- **Feel**: Personal photo blog aesthetic

### Layout Structure

#### Homepage (/)
- Header with site title "Gallery" centered
- Grid of album covers (3-4 per row desktop, 2 tablet, 1 mobile)
- Each cover shows: cover photo, album title, short description (max 50 chars)
- Footer with copyright

#### Album Page (/TYTULALBUMU)
- Header with album title (large)
- Full description below title (optional)
- Grid of photos (3-4 per row)
- Each photo: image, optional title/description
- Rating system on each photo

#### Admin Panel (/panel)
- Login screen with password "st3fan0"
- Dashboard showing all albums
- Create/Edit/Delete albums
- Upload photos with optimization
- Form fields:
  - Album: title, cover image, short description (max 50 chars), full description (optional)
  - Photo: image, title (optional), description (optional)

### Components

#### Album Card
- Cover image (16:9 or 4:3 ratio)
- Title below (bold)
- Short description (max 50 chars, truncated)
- Hover: subtle lift with shadow
- Border radius: 4px

#### Photo Card
- Image display
- Optional title overlay on hover
- Click to expand/lightbox
- Rating stars below

#### Login Form
- Simple centered box
- Password field
- Submit button
- Error messages inline

#### Loading Animation
- Custom spinner using theme colors
- Fade-in animations for content

### Animations
- Page transitions: fade (200ms)
- Loading spinner: rotating circle
- Hover effects: subtle scale/lift
- Image upload: progress bar
- Cards: fade-in on load (staggered)

## Functionality Specification

### Backend (Flask)

#### Database Models

**Album**
- id (primary key)
- title (unique, slug-friendly URL)
- cover_image (filename)
- short_description (max 50 chars)
- full_description (optional, text)
- created_at (timestamp)
- updated_at (timestamp)

**Photo**
- id (primary key)
- album_id (foreign key)
- filename (original)
- optimized_filename (web-optimized)
- title (optional)
- description (optional)
- created_at (timestamp)

**User**
- id (primary key)
- username (unique)
- password_hash
- ip_address
- created_at (timestamp)

**Rating**
- id (primary key)
- photo_id (foreign key)
- user_id (foreign key)
- score (1-5)
- created_at (timestamp)

**IP Registration**
- id (primary key)
- ip_address
- last_registration (timestamp)
- accounts_created (count)

#### API Endpoints

**Public**
- GET /api/albums - List all albums
- GET /api/albums/<slug> - Get single album with photos
- POST /api/register - Register new user
- POST /api/login - User login
- POST /api/rate - Rate a photo (requires auth)

**Admin (protected)**
- POST /api/admin/login - Admin login
- POST /api/admin/albums - Create album
- PUT /api/admin/albums/<id> - Update album
- DELETE /api/admin/albums/<id> - Delete album
- POST /api/admin/photos - Upload photo
- PUT /api/admin/photos/<id> - Update photo
- DELETE /api/admin/photos/<id> - Delete photo

#### Image Optimization
- Max width: 1920px
- Quality: 85%
- Format: JPEG
- Thumbnail generation: 400px width

### Frontend (React)

#### Pages
1. Home (/) - Album grid
2. Album (/TYTULALBUMU) - Photo grid with ratings
3. Admin Login (/panel) - Password entry
4. Admin Dashboard (/panel/dashboard) - Album management

#### User Authentication
- Register: username, password
- Login: username, password
- Session stored in localStorage
- Protected routes for rating

#### Rate Limiting (Frontend display)
- Show IP registration limit message
- Display cooldown timer

## Acceptance Criteria

1. ✓ Homepage displays album grid with covers
2. ✓ Album pages show all photos with titles/descriptions
3. ✓ Admin panel accessible only with correct password
4. ✓ Image upload with optimization works
5. ✓ User registration with IP limits enforced
6. ✓ Photo rating system works
7. ✓ 2015-style design (not neon/modern)
8. ✓ Loading animations present
9. ✓ Runs on localhost:21523
10. ✓ All data persisted in SQLite database

## Technical Stack
- **Backend**: Flask, SQLAlchemy, Pillow (image processing)
- **Frontend**: React + Vite
- **Database**: SQLite
- **Port**: 21523
