// ---- VIBE MAP JavaScript ----

document.addEventListener('DOMContentLoaded', function() {

  // ---- Flash Messages Auto-Remove ----
  const flashes = document.querySelectorAll('.flash-msg');
  flashes.forEach(f => {
    setTimeout(() => { if(f.parentNode) f.remove(); }, 3000);
  });

  // ---- Geolocation Helper ----
  function getLocation(callback) {
    if (!navigator.geolocation) {
      callback(null, null);
      return;
    }
    navigator.geolocation.getCurrentPosition(
      pos => callback(pos.coords.latitude, pos.coords.longitude),
      () => callback(null, null),
      { enableHighAccuracy: false, timeout: 10000 }
    );
  }

  // ---- Near Me Button ----
  const nearMeBtn = document.getElementById('nearMeBtn');
  if (nearMeBtn) {
    nearMeBtn.addEventListener('click', function() {
      this.innerHTML = '📍 Locating...';
      getLocation(function(lat, lng) {
        if (lat && lng) {
          const url = new URL(window.location.href);
          url.searchParams.set('lat', lat);
          url.searchParams.set('lng', lng);
          window.location.href = url.toString();
        } else {
          this.innerHTML = '📍 Near Me';
          alert('Location access denied. Please enable location.');
        }
      });
    });
  }

  // ---- Search Form ----
  const searchForm = document.getElementById('searchForm');
  if (searchForm) {
    searchForm.addEventListener('submit', function(e) {
      const q = this.querySelector('input[name="q"]').value.trim();
      if (!q) e.preventDefault();
    });
  }

  // ---- Category Buttons ----
  document.querySelectorAll('.cat-btn[data-category]').forEach(btn => {
    btn.addEventListener('click', function() {
      const cat = this.dataset.category;
      let url = '/search?category=' + encodeURIComponent(cat);
      const params = new URLSearchParams(window.location.search);
      if (params.get('lat')) url += '&lat=' + params.get('lat');
      if (params.get('lng')) url += '&lng=' + params.get('lng');
      window.location.href = url;
    });
  });

  // ---- Star Rating ----
  const starContainer = document.getElementById('starRating');
  const ratingInput = document.getElementById('ratingInput');
  if (starContainer && ratingInput) {
    const stars = starContainer.querySelectorAll('.star');
    stars.forEach(star => {
      star.addEventListener('click', function() {
        const val = parseInt(this.dataset.value);
        ratingInput.value = val;
        stars.forEach(s => {
          s.classList.toggle('active', parseInt(s.dataset.value) <= val);
        });
      });
      star.addEventListener('mouseenter', function() {
        const val = parseInt(this.dataset.value);
        stars.forEach(s => {
          s.style.color = parseInt(s.dataset.value) <= val ? '#ffcc00' : '#333';
        });
      });
    });
    starContainer.addEventListener('mouseleave', function() {
      const val = parseInt(ratingInput.value) || 0;
      stars.forEach(s => {
        s.style.color = '';
        s.classList.toggle('active', parseInt(s.dataset.value) <= val);
      });
    });
  }

  // ---- Tag Selection ----
  document.querySelectorAll('.tag-option').forEach(tag => {
    tag.addEventListener('click', function() {
      this.classList.toggle('selected');
      const checkbox = this.querySelector('input[type="checkbox"]');
      if (checkbox) checkbox.checked = this.classList.contains('selected');
    });
  });

  // ---- Character Counter ----
  const reviewTextarea = document.getElementById('reviewText');
  const charCount = document.getElementById('charCount');
  if (reviewTextarea && charCount) {
    reviewTextarea.addEventListener('input', function() {
      charCount.textContent = this.value.length + '/300';
      charCount.style.color = this.value.length > 300 ? '#ff3b30' : '#777';
    });
  }

  // ---- Photo Upload ----
  const uploadArea = document.getElementById('uploadArea');
  const fileInput = document.getElementById('photoInput');
  const cameraInput = document.getElementById('cameraInput');
  const previewImg = document.getElementById('previewImg');

  if (uploadArea && fileInput) {
    uploadArea.addEventListener('click', function(e) {
      if (e.target.closest('.upload-opt-btn')) return;
      if (this.classList.contains('has-photo')) return;
      fileInput.click();
    });

    fileInput.addEventListener('change', function() {
      if (this.files && this.files[0]) {
        showPreview(this.files[0]);
      }
    });

    if (cameraInput) {
      cameraInput.addEventListener('change', function() {
        if (this.files && this.files[0]) {
          showPreview(this.files[0]);
        }
      });
    }
  }

  function showPreview(file) {
    if (!file.type.startsWith('image/')) {
      alert('Please select an image file.');
      return;
    }
    if (file.size > 5 * 1024 * 1024) {
      alert('Image must be under 5MB.');
      return;
    }
    const reader = new FileReader();
    reader.onload = function(e) {
      if (previewImg) {
        previewImg.src = e.target.result;
        previewImg.style.display = 'block';
      }
      if (uploadArea) {
        uploadArea.classList.add('has-photo');
        uploadArea.querySelector('.upload-content').style.display = 'none';
        uploadArea.querySelector('.upload-options')?.remove();
      }
    };
    reader.readAsDataURL(file);
  }

  // ---- Vibe Check Form Submit ----
  const vcForm = document.getElementById('vibeCheckForm');
  if (vcForm) {
    vcForm.addEventListener('submit', function(e) {
      const photo = fileInput ? fileInput.files[0] : null;
      const cameraPhoto = cameraInput ? cameraInput.files[0] : null;
      const hasPhoto = photo || cameraPhoto;

      if (!hasPhoto && !previewImg?.src) {
        e.preventDefault();
        alert('NO PHOTO = NO VIBE CHECK 👀 Upload a photo!');
        return;
      }

      const rating = document.getElementById('ratingInput')?.value;
      if (!rating || rating < 1) {
        e.preventDefault();
        alert('Please rate the vibe!');
        return;
      }

      // Capture location
      if (!document.getElementById('latInput').value) {
        getLocation(function(lat, lng) {
          if (lat && lng) {
            document.getElementById('latInput').value = lat;
            document.getElementById('lngInput').value = lng;
          }
          vcForm.submit();
        });
        e.preventDefault();
      }
    });
  }

  // ---- Lightbox ----
  const lightbox = document.getElementById('lightbox');
  const lightboxImg = document.getElementById('lightboxImg');

  document.querySelectorAll('[data-lightbox]').forEach(img => {
    img.addEventListener('click', function() {
      if (lightbox && lightboxImg) {
        lightboxImg.src = this.src;
        lightbox.classList.add('show');
      }
    });
  });

  if (lightbox) {
    lightbox.addEventListener('click', function() {
      this.classList.remove('show');
    });
  }

  // ---- Report Modal ----
  const reportModal = document.getElementById('reportModal');
  const reportForm = document.getElementById('reportForm');

  document.querySelectorAll('.vibe-report').forEach(btn => {
    btn.addEventListener('click', function(e) {
      e.preventDefault();
      const vcId = this.dataset.vibeId;
      if (reportForm) {
        reportForm.action = '/report/' + vcId;
      }
      if (reportModal) {
        reportModal.classList.add('show');
      }
    });
  });

  if (reportModal) {
    reportModal.addEventListener('click', function(e) {
      if (e.target === this) this.classList.remove('show');
    });
    const closeBtn = reportModal.querySelector('.modal-close');
    if (closeBtn) {
      closeBtn.addEventListener('click', function() {
        reportModal.classList.remove('show');
      });
    }
  }

  // ---- Admin Tabs ----
  document.querySelectorAll('.admin-tab').forEach(tab => {
    tab.addEventListener('click', function() {
      const target = this.dataset.tab;
      document.querySelectorAll('.admin-tab').forEach(t => t.classList.remove('active'));
      document.querySelectorAll('.admin-panel').forEach(p => p.classList.remove('active'));
      this.classList.add('active');
      document.getElementById('panel-' + target)?.classList.add('active');
    });
  });

  // ---- Filter Buttons (Explore) ----
  const filterBtns = document.querySelectorAll('.filter-btn[data-category]');
  filterBtns.forEach(btn => {
    btn.addEventListener('click', function(e) {
      e.preventDefault();
      let url = '/explore';
      const params = new URLSearchParams(window.location.search);
      if (this.dataset.category) {
        params.set('category', this.dataset.category);
      } else {
        params.delete('category');
      }
      if (params.toString()) url += '?' + params.toString();
      window.location.href = url;
    });
  });

  // ---- Sort Buttons (Explore) ----
  const sortBtns = document.querySelectorAll('.sort-btn[data-sort]');
  sortBtns.forEach(btn => {
    btn.addEventListener('click', function() {
      const params = new URLSearchParams(window.location.search);
      params.set('sort', this.dataset.sort);
      window.location.href = '/explore?' + params.toString();
    });
  });

  // ---- Scroll Animations ----
  const observer = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        entry.target.classList.add('animate-in');
        observer.unobserve(entry.target);
      }
    });
  }, { threshold: 0.1 });

  document.querySelectorAll('.place-card, .vibe-card').forEach(el => {
    observer.observe(el);
  });

  // ---- Auto-get location on homepage ----
  if (window.location.pathname === '/' && !new URLSearchParams(window.location.search).get('lat')) {
    // Try to get location silently
    getLocation(function(lat, lng) {
      if (lat && lng) {
        const url = new URL(window.location.href);
        url.searchParams.set('lat', lat);
        url.searchParams.set('lng', lng);
        // Update links but don't reload
        document.querySelectorAll('a[href*="/search"], a[href*="/explore"], a.cat-btn').forEach(a => {
          const href = new URL(a.href);
          href.searchParams.set('lat', lat);
          href.searchParams.set('lng', lng);
          a.href = href.toString();
        });
        // Update search form
        const form = document.getElementById('searchForm');
        if (form) {
          let latField = form.querySelector('input[name="lat"]');
          let lngField = form.querySelector('input[name="lng"]');
          if (!latField) {
            latField = document.createElement('input');
            latField.type = 'hidden'; latField.name = 'lat';
            form.appendChild(latField);
          }
          if (!lngField) {
            lngField = document.createElement('input');
            lngField.type = 'hidden'; lngField.name = 'lng';
            form.appendChild(lngField);
          }
          latField.value = lat;
          lngField.value = lng;
        }
        // Store for later use
        window._userLat = lat;
        window._userLng = lng;
      }
    });
  }

});