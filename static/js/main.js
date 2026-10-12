document.addEventListener('DOMContentLoaded', function() {

    // --- Product catalog filters ---
    const homePageContent = document.querySelector('.main-content-grid');
    if (homePageContent) {
        const params = new URLSearchParams(window.location.search);

        function updateQueryParam(name, value) {
            const url = new URL(window.location.href);
            if (value) {
                url.searchParams.set(name, value);
            } else {
                url.searchParams.delete(name);
            }
            // A new filter or ordering starts on the first page.
            url.searchParams.delete('page');
            window.location.href = url.toString();
        }

        const searchForm = homePageContent.querySelector('#product-search-form');
        if (searchForm) {
            searchForm.addEventListener('submit', function(event) {
                event.preventDefault();
                updateQueryParam('search', searchForm.querySelector('.search-input').value.trim());
            });
        }

        const sortButtons = homePageContent.querySelectorAll('.sort-options .sort-button');
        const sorting = params.get('sorting') || '-created_at';
        sortButtons.forEach(button => {
            const active = button.dataset.sorting === sorting;
            button.classList.toggle('active-sort', active);
            button.setAttribute('aria-pressed', String(active));
            button.addEventListener('click', function() {
                updateQueryParam('sorting', button.dataset.sorting);
            });
        });

        const selectedCategories = new Set((params.get('categories') || '').split(',').filter(Boolean));
        const keywordsList = homePageContent.querySelector('.keywords-list');
        const checkboxes = homePageContent.querySelectorAll('.checkbox-group input[name="categories"]');

        checkboxes.forEach(checkbox => {
            const category = checkbox.value;
            checkbox.checked = selectedCategories.has(category);
            checkbox.addEventListener('change', function() {
                if (checkbox.checked) {
                    selectedCategories.add(category);
                } else {
                    selectedCategories.delete(category);
                }
                updateQueryParam('categories', [...selectedCategories].join(','));
            });

            if (keywordsList && checkbox.checked) {
                const tag = document.createElement('span');
                tag.className = 'keyword-tag';
                tag.dataset.keyword = category;
                tag.textContent = checkbox.dataset.label;

                const removeButton = document.createElement('button');
                removeButton.type = 'button';
                removeButton.className = 'fa-solid fa-xmark remove-keyword-icon';
                removeButton.setAttribute('aria-label', `Remove ${checkbox.dataset.label}`);
                removeButton.addEventListener('click', function() {
                    selectedCategories.delete(category);
                    updateQueryParam('categories', [...selectedCategories].join(','));
                });
                tag.appendChild(removeButton);
                keywordsList.appendChild(tag);
            }
        });
    }

    // --- Logic for Product Detail Pages (product-*.html) ---
    const productPageContent = document.querySelector('.page-product');
    if (productPageContent) {
        // Accordion
        const accordionTitle = document.querySelector('.accordion-title');
        if (accordionTitle) {
            accordionTitle.addEventListener('click', function () {
                this.closest('.accordion-item').classList.toggle('active');
            });
        }
    }

    // --- Logic for Account and Admin Pages ---
    const accountAdminWrapper = document.querySelector('.account-page-wrapper, .admin-page-wrapper');
    if (accountAdminWrapper) {
        // Account Page Tabs
        const accountTabs = document.querySelectorAll('.account-tab');
        const tabPanes = document.querySelectorAll('.tab-pane');
        if (accountTabs.length > 0 && tabPanes.length > 0) {
            accountTabs.forEach(tab => {
                tab.addEventListener('click', function() {
                    accountTabs.forEach(item => item.classList.remove('active'));
                    tabPanes.forEach(pane => pane.classList.remove('active'));
                    const targetPane = document.querySelector(this.dataset.tabTarget);
                    this.classList.add('active');
                    if (targetPane) targetPane.classList.add('active');
                });
            });
        }

        // Admin Panel - Category Tags
        const categoryTagsContainer = document.querySelector('.category-tags');
        if (categoryTagsContainer) {
            categoryTagsContainer.addEventListener('click', function(e) {
                const clickedTag = e.target.closest('.category-tag');
                if (clickedTag) {
                    categoryTagsContainer.querySelectorAll('.category-tag').forEach(t => t.classList.remove('active'));
                    clickedTag.classList.add('active');
                }
            });
        }

        // Image Upload Simulation
        const uploadButton = document.getElementById('upload-image-btn');
        const fileInput = document.getElementById('image-upload-input');

        if (uploadButton && fileInput) {
            uploadButton.addEventListener('click', function() {
                fileInput.click();
            });

            fileInput.addEventListener('change', function(event) {
                const file = event.target.files[0];
                if (file) {
                    const reader = new FileReader();
                    const placeholder = document.querySelector('.image-upload-placeholder');

                    reader.onload = function(e) {
                        placeholder.innerHTML = '';
                        placeholder.style.backgroundImage = `url('${e.target.result}')`;
                        placeholder.style.backgroundSize = 'cover';
                        placeholder.style.backgroundPosition = 'center';
                    }
                    reader.readAsDataURL(file);
                }
            });
        }
    }
    });