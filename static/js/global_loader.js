document.addEventListener('DOMContentLoaded', () => {
    document.querySelectorAll('.btn, button').forEach(btn => {
        btn.addEventListener('click', function(e) {
            // Exclude empty buttons or non-actionable elements
            if (!this.innerText.trim() && !this.innerHTML.trim()) return;
            
            // Prevent modifying if it's already loading
            if (this.classList.contains('is-loading')) {
                e.preventDefault();
                return;
            }

            // Exclude specific buttons if needed
            if (this.classList.contains('no-loader')) return;

            // Add loading class
            this.classList.add('is-loading');

            // Save original content
            const originalContent = this.innerHTML;
            
            // Get computed width to prevent button from resizing/jumping
            const currentWidth = this.offsetWidth;
            if (currentWidth > 0) {
                this.style.width = `${currentWidth}px`;
            }
            
            // Set spinner
            this.innerHTML = '<i class="fa-solid fa-circle-notch fa-spin"></i> Loading...';

            // If it's a submit button inside a form, let the form submit normally
            if (this.type === 'submit') {
                setTimeout(() => {
                    this.disabled = true;
                }, 50); // delay ensures the submit event fires
            } else if (this.tagName === 'BUTTON') {
                // If it's just a button (e.g. AJAX), disable it
                this.disabled = true;
            } else if (this.tagName === 'A') {
                // If it's a link, disable via CSS pointer-events
                this.style.pointerEvents = 'none';
            }
            
            // Fallback: Restore original content after 8 seconds just in case it was a download or an AJAX request
            setTimeout(() => {
                if (this.classList.contains('is-loading')) {
                    this.innerHTML = originalContent;
                    this.classList.remove('is-loading');
                    this.disabled = false;
                    this.style.width = '';
                    this.style.pointerEvents = '';
                }
            }, 8000); 
        });
    });
});
