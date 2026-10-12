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
            accordionTitle.addEventListener('click', function() {
                this.closest('.accordion-item').classList.toggle('active');
            });
        }
        // "Add to Cart" Button and Counter
//        const cartControls = document.querySelector('.cart-controls');
//        if (cartControls) {
//            const addToCartBtn = cartControls.querySelector('#add-to-cart-btn');
//            const quantityCounter = cartControls.querySelector('#quantity-counter');
//            const decreaseBtn = quantityCounter.querySelector('[data-action="decrease"]');
//            const increaseBtn = quantityCounter.querySelector('[data-action="increase"]');
//            const quantityValueSpan = quantityCounter.querySelector('.quantity-value');
//            let quantity = 0;
//            function updateView() {
//                if (quantity === 0) {
//                    addToCartBtn.classList.remove('is-hidden');
//                    quantityCounter.classList.add('is-hidden');
//                } else {
//                    addToCartBtn.classList.add('is-hidden');
//                    quantityCounter.classList.remove('is-hidden');
//                    quantityValueSpan.textContent = `${quantity} in cart`;
//                }
//            }
//            addToCartBtn.addEventListener('click', function() { quantity = 1; updateView(); });
//            decreaseBtn.addEventListener('click', function() { if (quantity > 0) { quantity--; updateView(); } });
//            increaseBtn.addEventListener('click', function() { quantity++; updateView(); });
//            updateView();
//        }
    }

//    // --- Logic for Cart Page (cart.html) ---
//    const cartPageContent = document.querySelector('.cart-page-wrapper');
//    if (cartPageContent) {
//        const cartItemsList = document.getElementById('cart-items-list');
//        const cartTotalPriceElem = document.getElementById('cart-total-price');
//        function updateCartTotal() {
//            let total = 0;
//            document.querySelectorAll('.cart-item').forEach(item => {
//                const priceText = item.querySelector('[data-item-total-price]').textContent;
//                if (priceText) {
//                    total += parseFloat(priceText.replace('$', ''));
//                }
//            });
//            if (cartTotalPriceElem) cartTotalPriceElem.textContent = `$${total.toFixed(2)}`;
//        }
//        if (cartItemsList) {
//            cartItemsList.addEventListener('click', function(event) {
//                const cartItem = event.target.closest('.cart-item');
//                if (!cartItem) return;
//                const quantityElem = cartItem.querySelector('.quantity-value-cart');
//                const itemTotalElem = cartItem.querySelector('[data-item-total-price]');
//                const basePrice = parseFloat(cartItem.dataset.price);
//                let quantity = parseInt(quantityElem.textContent);
//                if (event.target.closest('[data-action="increase"]')) {
//                    quantity++;
//                } else if (event.target.closest('[data-action="decrease"]')) {
//                    quantity = quantity > 1 ? quantity - 1 : 0;
//                }
//                if (event.target.closest('[data-action="remove"]') || quantity === 0) {
//                    cartItem.remove();
//                } else {
//                    quantityElem.textContent = quantity;
//                    itemTotalElem.textContent = `$${(basePrice * quantity).toFixed(2)}`;
//                }
//                updateCartTotal();
//            });
//        }
//        updateCartTotal();
//    }

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