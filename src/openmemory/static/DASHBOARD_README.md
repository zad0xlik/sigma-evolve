# SIGMA Dashboard - Refactored Architecture

## Overview

The dashboard has been completely refactored from a single 800+ line HTML file into a modern, modular architecture using Alpine.js for reactive state management.

## File Structure

```
src/openmemory/static/
├── dashboard.html          # Main HTML (400 lines, Alpine.js templates)
├── DASHBOARD_README.md     # This file
├── css/
│   ├── base.css           # Base styles, layout, typography
│   ├── components.css     # Component styles (cards, buttons, forms)
│   ├── tabs.css           # Tab navigation styles
│   └── theme.css          # Theme, animations, colors
├── js/
│   ├── api.js             # API layer - all backend calls
│   ├── utils.js           # Utility functions (formatting, validation)
│   ├── dashboard.js       # Main Alpine.js component
│   └── forms/
│       ├── projectForm.js # Project registration form logic
│       └── workerForm.js  # Worker control form logic
```

## Architecture

### CSS Organization (4 Files)

1. **base.css** - Foundation styles
   - CSS reset
   - Body & container
   - Header & typography
   - Grid layouts
   - Mobile responsive

2. **components.css** - UI Components
   - Cards (stat, proposal, experiment, worker, pattern, project)
   - Badges & buttons
   - Forms & inputs
   - Health indicators
   - Toast notifications
   - Loading spinners

3. **tabs.css** - Tab Navigation
   - Tab styles
   - Content sections
   - Active states

4. **theme.css** - Theming & Animation
   - CSS variables
   - Gradient utilities
   - Animations (fadeIn, slideDown, pulse, etc.)
   - Scrollbar & selection styling
   - Dark mode support (prepared)

### JavaScript Organization (6 Files)

1. **api.js** - API Layer
   - All fetch calls centralized
   - Methods for dashboard, proposals, experiments, workers, patterns, projects
   - Error handling

2. **utils.js** - Utilities
   - Date/time formatting
   - Confidence formatting
   - Toast notifications
   - URL validation
   - LocalStorage helpers
   - Clipboard operations
   - Debounce function

3. **dashboard.js** - Main Alpine Component
   - State management (currentTab, loading, data)
   - Init method (loads saved preferences)
   - Tab switching
   - Data refresh (manual & auto every 30s)
   - Proposal actions
   - Toast management
   - Keyboard shortcuts (Cmd/Ctrl+R, Cmd/Ctrl+1-5)

4. **forms/projectForm.js** - Project Registration
   - Form state & validation
   - Submit handler
   - Success callback (refreshes projects)
   - Optional prompt to start analysis

5. **forms/workerForm.js** - Worker Control
   - Form state & validation
   - Worker type selection (5 types)
   - Project dropdown (populated from API)
   - Advanced options (iterations, dream probability)
   - Submit handler

## Features

### Existing Features (Enhanced)
- ✅ Dashboard statistics
- ✅ Tab navigation (Proposals, Experiments, Workers, Patterns, Projects)
- ✅ Proposal viewing & approval/rejection
- ✅ Experiment tracking
- ✅ Worker statistics
- ✅ Pattern library
- ✅ Project listing
- ✅ Auto-refresh (30 seconds)
- ✅ Manual refresh button

### New Features
- ✅ **Project Registration Form** - Register new projects directly from UI
- ✅ **Worker Control Form** - Start workers with configuration
- ✅ **Toast Notifications** - Elegant toast system (replaces alerts)
- ✅ **Loading Indicators** - Spinners during API calls
- ✅ **Form Validation** - Client-side validation with error messages
- ✅ **Keyboard Shortcuts** 
  - `Cmd/Ctrl + R` - Refresh data
  - `Cmd/Ctrl + 1-5` - Switch tabs
- ✅ **LocalStorage** - Remembers selected tab
- ✅ **Collapsible Forms** - Forms can be expanded/collapsed
- ✅ **Advanced Options** - Optional worker configuration
- ✅ **Responsive Design** - Mobile-friendly

## Usage

### Registering a New Project

1. Go to **Projects** tab
2. Click "Register New Project" form header to expand
3. Fill in:
   - Repository URL (required) - e.g., `https://github.com/username/repo`
   - Branch (optional, default: "main")
   - Language (required) - Select from dropdown
   - Framework (optional) - e.g., "fastapi", "react"
   - Domain (optional) - e.g., "investment-research"
4. Click "Register Project"
5. Optionally start analysis when prompted

### Starting a Worker

1. Go to **Workers** tab
2. Click "Start Worker" form header to expand
3. Select:
   - Worker Type (required) - Choose from 5 types
   - Project (required) - Select registered project
4. Optionally expand "Advanced Options":
   - Max Iterations (1-100, default: 5)
   - Dream Probability (0-100%, default: 15%)
5. Click "Start Worker"

### Approving/Rejecting Proposals

1. Go to **Proposals** tab
2. Find a proposal with "pending" status
3. Click "✓ Approve" or "✗ Reject"
4. Toast notification confirms action
5. Proposal status updates automatically

## Keyboard Shortcuts

- `Cmd/Ctrl + R` - Refresh all data
- `Cmd/Ctrl + 1` - Switch to Proposals tab
- `Cmd/Ctrl + 2` - Switch to Experiments tab
- `Cmd/Ctrl + 3` - Switch to Workers tab
- `Cmd/Ctrl + 4` - Switch to Patterns tab
- `Cmd/Ctrl + 5` - Switch to Projects tab

## Technology Stack

- **Alpine.js 3.x** - Reactive state management
- **ES6 Modules** - Modern JavaScript imports/exports
- **Fetch API** - HTTP requests
- **CSS3** - Modern styling with variables, animations
- **LocalStorage** - Persist user preferences

## Development

### Adding a New Tab

1. Add tab button in `dashboard.html`:
```html
<button class="tab" :class="{ active: currentTab === 'mytab' }" @click="switchTab('mytab')">
    🔥 My Tab
</button>
```

2. Add content section:
```html
<div x-show="currentTab === 'mytab'" class="content-section" x-transition>
    <h2>My Tab Title</h2>
    <!-- Your content -->
</div>
```

3. Add data loading in `dashboard.js`:
```javascript
case 'mytab':
    this.mydata = await api.getMyData();
    break;
```

4. Add API method in `api.js`:
```javascript
async getMyData() {
    const response = await fetch(`${API_BASE}/api/my-endpoint`);
    if (!response.ok) throw new Error('Failed to fetch');
    return response.json();
}
```

### Adding a New Form

1. Create form component in `js/forms/myForm.js`:
```javascript
export function myForm() {
    return {
        isOpen: false,
        form: { /* fields */ },
        toggle() { this.isOpen = !this.isOpen; },
        async submit() { /* logic */ }
    };
}
window.myForm = myForm;
```

2. Import in `dashboard.html`:
```html
<script type="module">
    import { myForm } from './js/forms/myForm.js';
    window.myForm = myForm;
</script>
```

3. Add form in HTML:
```html
<div class="form-container" x-data="myForm()">
    <div class="form-header" @click="toggle()">
        <div class="form-title">My Form</div>
        <button class="form-toggle" :class="{ collapsed: !isOpen }">▼</button>
    </div>
    <div x-show="isOpen" x-transition>
        <form @submit.prevent="submit()">
            <!-- Form fields -->
        </form>
    </div>
</div>
```

## Browser Compatibility

- Chrome/Edge 90+
- Firefox 88+
- Safari 14+
- Mobile browsers (iOS Safari, Chrome Android)

## Performance

- **Initial Load**: ~50KB total (HTML + CSS + JS)
- **Alpine.js CDN**: ~15KB gzipped
- **API Calls**: Optimized with auto-refresh (30s interval)
- **LocalStorage**: Minimal usage (tab preference only)

## Future Enhancements

- [ ] Dark mode toggle
- [ ] Export proposals/experiments to CSV
- [ ] Proposal diff viewer (before/after code)
- [ ] Worker logs streaming
- [ ] Real-time updates (WebSocket)
- [ ] Proposal filtering & sorting
- [ ] Search functionality
- [ ] Chart visualizations for metrics
- [ ] Bulk operations
- [ ] Notification preferences
- [ ] Custom refresh intervals

## Troubleshooting

### Forms not working
- Check browser console for errors
- Ensure modules are loaded correctly
- Verify Alpine.js CDN is accessible

### API calls failing
- Check that backend server is running
- Verify API endpoints in network tab
- Check CORS settings

### Styles not loading
- Verify CSS files are served correctly
- Check `/static/css/` path
- Clear browser cache

### Alpine not reactive
- Ensure `x-data` is on container
- Check Alpine is loaded (`defer` script tag)
- Verify component functions are registered globally

## Support

For issues or questions:
1. Check browser console for errors
2. Review network tab for failed requests
3. Verify all files are in correct locations
4. Test with browser dev tools open

---

**Version**: 2.0.0 (Refactored)  
**Last Updated**: January 15, 2026  
**Framework**: Alpine.js 3.x
