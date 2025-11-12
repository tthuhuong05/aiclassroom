// Modern VirtualRoom JavaScript
class ModernVirtualRoom {
    constructor() {
        this.init();
    }

    init() {
        this.setupDarkMode();
        this.setupParticles();
        this.setupAnimations();
        this.setupNavbar();
        this.setupScrollEffects();
        this.setupCourseCards();
        this.setupNewsletter();
    }

    // Dark Mode Toggle
    setupDarkMode() {
        const toggleBtn = document.createElement('button');
        toggleBtn.className = 'dark-mode-toggle';
        toggleBtn.innerHTML = '<i class="bi bi-moon-stars-fill"></i>';
        toggleBtn.title = 'Toggle Dark Mode';

        // Check for saved theme preference or default to light mode
        const savedTheme = localStorage.getItem('theme');
        const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;

        if (savedTheme === 'dark' || (!savedTheme && prefersDark)) {
            document.body.classList.add('dark-mode');
            toggleBtn.innerHTML = '<i class="bi bi-sun-fill"></i>';
        }

        toggleBtn.addEventListener('click', () => {
            document.body.classList.toggle('dark-mode');
            const isDark = document.body.classList.contains('dark-mode');

            // Update icon
            toggleBtn.innerHTML = isDark
                ? '<i class="bi bi-sun-fill"></i>'
                : '<i class="bi bi-moon-stars-fill"></i>';

            // Save preference
            localStorage.setItem('theme', isDark ? 'dark' : 'light');

            // Animate toggle button
            toggleBtn.style.transform = 'scale(1.2)';
            setTimeout(() => {
                toggleBtn.style.transform = '';
            }, 200);
        });

        document.body.appendChild(toggleBtn);
    }

    // Particle System for Hero Section
    setupParticles() {
        const heroSection = document.querySelector('.hero-section');
        if (!heroSection) return;

        const canvas = document.createElement('canvas');
        canvas.className = 'hero-particles';
        canvas.style.position = 'absolute';
        canvas.style.top = '0';
        canvas.style.left = '0';
        canvas.style.width = '100%';
        canvas.style.height = '100%';
        canvas.style.pointerEvents = 'none';

        heroSection.appendChild(canvas);

        const ctx = canvas.getContext('2d');
        let particles = [];
        let animationId;

        const resizeCanvas = () => {
            canvas.width = heroSection.offsetWidth;
            canvas.height = heroSection.offsetHeight;
        };

        const createParticle = () => {
            return {
                x: Math.random() * canvas.width,
                y: Math.random() * canvas.height,
                vx: (Math.random() - 0.5) * 0.5,
                vy: (Math.random() - 0.5) * 0.5,
                size: Math.random() * 2 + 1,
                opacity: Math.random() * 0.5 + 0.2
            };
        };

        const initParticles = () => {
            particles = [];
            const particleCount = Math.min(50, Math.floor((canvas.width * canvas.height) / 15000));

            for (let i = 0; i < particleCount; i++) {
                particles.push(createParticle());
            }
        };

        const updateParticles = () => {
            particles.forEach(particle => {
                particle.x += particle.vx;
                particle.y += particle.vy;

                // Wrap around edges
                if (particle.x < 0) particle.x = canvas.width;
                if (particle.x > canvas.width) particle.x = 0;
                if (particle.y < 0) particle.y = canvas.height;
                if (particle.y > canvas.height) particle.y = 0;
            });
        };

        const drawParticles = () => {
            ctx.clearRect(0, 0, canvas.width, canvas.height);

            particles.forEach(particle => {
                ctx.beginPath();
                ctx.arc(particle.x, particle.y, particle.size, 0, Math.PI * 2);
                ctx.fillStyle = `rgba(255, 255, 255, ${particle.opacity})`;
                ctx.fill();
            });
        };

        const animate = () => {
            updateParticles();
            drawParticles();
            animationId = requestAnimationFrame(animate);
        };

        // Initialize
        resizeCanvas();
        initParticles();
        animate();

        // Handle resize
        window.addEventListener('resize', () => {
            resizeCanvas();
            initParticles();
        });
    }

    // Scroll-triggered Animations
    setupAnimations() {
        const observerOptions = {
            threshold: 0.1,
            rootMargin: '0px 0px -50px 0px'
        };

        const observer = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    entry.target.classList.add('fade-in-up');
                }
            });
        }, observerOptions);

        // Observe elements
        document.querySelectorAll('.course-card, .section-header, .footer-links').forEach(el => {
            observer.observe(el);
        });
    }

    // Enhanced Navbar
    setupNavbar() {
        const navbar = document.querySelector('.navbar');

        // Add scroll effect
        const handleScroll = () => {
            if (window.scrollY > 50) {
                navbar.classList.add('navbar-scrolled');
            } else {
                navbar.classList.remove('navbar-scrolled');
            }
        };

        window.addEventListener('scroll', handleScroll);

        // Enhanced dropdown animations
        const dropdowns = document.querySelectorAll('.dropdown');
        dropdowns.forEach(dropdown => {
            const menu = dropdown.querySelector('.dropdown-menu');

            dropdown.addEventListener('mouseenter', () => {
                menu.style.display = 'block';
                menu.style.opacity = '0';
                menu.style.transform = 'translateY(-10px)';

                requestAnimationFrame(() => {
                    menu.style.transition = 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)';
                    menu.style.opacity = '1';
                    menu.style.transform = 'translateY(0)';
                });
            });

            dropdown.addEventListener('mouseleave', () => {
                menu.style.opacity = '0';
                menu.style.transform = 'translateY(-10px)';

                setTimeout(() => {
                    menu.style.display = 'none';
                }, 300);
            });
        });
    }

    // Scroll Effects
    setupScrollEffects() {
        // Parallax effect for hero section
        const heroSlideshow = document.querySelector('.hero-slideshow');
        if (heroSlideshow) {
            const handleScroll = () => {
                const scrolled = window.pageYOffset;
                const rate = scrolled * -0.5;
                heroSlideshow.style.transform = `translateY(${rate}px)`;
            };

            window.addEventListener('scroll', handleScroll);
        }

        // Smooth scroll for anchor links
        document.querySelectorAll('a[href^="#"]').forEach(anchor => {
            anchor.addEventListener('click', function (e) {
                e.preventDefault();
                const target = document.querySelector(this.getAttribute('href'));
                if (target) {
                    target.scrollIntoView({
                        behavior: 'smooth',
                        block: 'start'
                    });
                }
            });
        });
    }

    // Enhanced Course Cards
    setupCourseCards() {
        const cards = document.querySelectorAll('.course-card');

        cards.forEach(card => {
            // Add hover sound effect (visual feedback)
            card.addEventListener('mouseenter', () => {
                card.style.transform = 'translateY(-8px) scale(1.02)';
            });

            card.addEventListener('mouseleave', () => {
                card.style.transform = '';
            });

            // Add click ripple effect
            card.addEventListener('click', function(e) {
                const ripple = document.createElement('div');
                ripple.className = 'ripple';
                ripple.style.left = e.offsetX + 'px';
                ripple.style.top = e.offsetY + 'px';

                this.appendChild(ripple);

                setTimeout(() => {
                    ripple.remove();
                }, 600);
            });
        });
    }

    // Newsletter Subscription
    setupNewsletter() {
        const newsletterForm = document.querySelector('.newsletter-form');
        if (!newsletterForm) return;

        newsletterForm.addEventListener('submit', async (e) => {
            e.preventDefault();

            const email = newsletterForm.querySelector('.newsletter-input').value;
            const submitBtn = newsletterForm.querySelector('.newsletter-btn');

            // Show loading state
            const originalText = submitBtn.textContent;
            submitBtn.innerHTML = '<div class="loading-spinner"></div>';
            submitBtn.disabled = true;

            try {
                // Simulate API call (replace with actual API)
                await new Promise(resolve => setTimeout(resolve, 2000));

                // Show success message
                submitBtn.innerHTML = '<i class="bi bi-check-circle-fill"></i>';
                submitBtn.style.background = 'var(--gradient-accent)';

                // Reset after 3 seconds
                setTimeout(() => {
                    submitBtn.innerHTML = originalText;
                    submitBtn.disabled = false;
                    submitBtn.style.background = '';
                    newsletterForm.reset();
                }, 3000);

            } catch (error) {
                // Show error message
                submitBtn.innerHTML = '<i class="bi bi-x-circle-fill"></i>';

                setTimeout(() => {
                    submitBtn.innerHTML = originalText;
                    submitBtn.disabled = false;
                }, 3000);
            }
        });
    }
}

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    new ModernVirtualRoom();
});

// Utility functions
const utils = {
    // Debounce function for performance
    debounce: (func, wait) => {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    },

    // Check if element is in viewport
    isInViewport: (element) => {
        const rect = element.getBoundingClientRect();
        return (
            rect.top >= 0 &&
            rect.left >= 0 &&
            rect.bottom <= (window.innerHeight || document.documentElement.clientHeight) &&
            rect.right <= (window.innerWidth || document.documentElement.clientWidth)
        );
    },

    // Get random number between min and max
    random: (min, max) => {
        return Math.random() * (max - min) + min;
    }
};

// Add CSS for ripple effect
const rippleStyle = document.createElement('style');
rippleStyle.textContent = `
    .ripple {
        position: absolute;
        border-radius: 50%;
        background: rgba(255, 255, 255, 0.6);
        transform: scale(0);
        animation: ripple 0.6s linear;
        pointer-events: none;
    }

    @keyframes ripple {
        to {
            transform: scale(4);
            opacity: 0;
        }
    }

    .course-card {
        position: relative;
        overflow: hidden;
    }

    .navbar-scrolled {
        background: rgba(255, 255, 255, 0.98) !important;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.1) !important;
    }
`;
document.head.appendChild(rippleStyle);

// Performance optimization: Lazy load images
const lazyLoadImages = () => {
    const images = document.querySelectorAll('img[data-src]');

    const imageObserver = new IntersectionObserver((entries, observer) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                const img = entry.target;
                img.src = img.dataset.src;
                img.removeAttribute('data-src');
                observer.unobserve(img);
            }
        });
    });

    images.forEach(img => imageObserver.observe(img));
};

// Initialize lazy loading
document.addEventListener('DOMContentLoaded', lazyLoadImages);

// Service Worker for PWA (optional)
if ('serviceWorker' in navigator) {
    window.addEventListener('load', () => {
        navigator.serviceWorker.register('/sw.js')
            .then(registration => console.log('SW registered'))
            .catch(error => console.log('SW registration failed'));
    });
}
