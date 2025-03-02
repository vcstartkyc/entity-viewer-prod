document.addEventListener('DOMContentLoaded', function() {
    const searchInput = document.getElementById('search-input');
    const datasetFilter = document.getElementById('dataset-filter');
    const entityGrid = document.getElementById('entity-grid');
    const loading = document.getElementById('loading');
    const error = document.getElementById('error');
    const noResults = document.getElementById('no-results');
    let debounceTimer;

    function createEntityCard(entity) {
        const card = document.createElement('div');
        card.className = 'entity-card';
        
        const name = document.createElement('h3');
        name.className = 'entity-name';
        name.textContent = entity.name || 'Unknown Entity';
        
        const reference = document.createElement('div');
        reference.className = 'entity-reference';
        reference.textContent = entity.reference || 'No reference';
        
        const tags = document.createElement('div');
        tags.className = 'entity-tags';
        
        // Add dataset tags
        if (entity.datasets && Array.isArray(entity.datasets)) {
            const datasetMap = {
                'sanctions': 'Sanctions',
                'pep': 'PEP',
                'adverse_media': 'Adverse Media',
                'insolvency': 'Insolvency',
                'disqualified': 'Disqualified'
            };
            
            entity.datasets.forEach(dataset => {
                const datasetTag = document.createElement('span');
                datasetTag.className = 'entity-tag';
                datasetTag.textContent = datasetMap[dataset] || dataset;
                tags.appendChild(datasetTag);
            });
        }
        
        // Add risk level tag if present
        if (entity.risk_level) {
            const riskTag = document.createElement('span');
            const riskLevel = entity.risk_level.toLowerCase();
            riskTag.className = `entity-tag ${riskLevel}-risk`;
            riskTag.textContent = entity.risk_level.replace(/_/g, ' ');
            tags.appendChild(riskTag);
        }
        
        const actions = document.createElement('div');
        actions.className = 'entity-actions';
        
        const viewButton = document.createElement('a');
        viewButton.href = `/entity/${entity.slug || slugify(entity.name)}`;
        viewButton.className = 'view-details-btn';
        viewButton.innerHTML = 'View Details <i class="fas fa-arrow-right"></i>';
        actions.appendChild(viewButton);
        
        card.appendChild(name);
        card.appendChild(reference);
        if (tags.children.length > 0) {
            card.appendChild(tags);
        }
        card.appendChild(actions);
        
        return card;
    }

    // Simple slugify function for fallback
    function slugify(text) {
        return text.toString().toLowerCase()
            .replace(/\s+/g, '-')           // Replace spaces with -
            .replace(/[^\w\-]+/g, '')       // Remove all non-word chars
            .replace(/\-\-+/g, '-')         // Replace multiple - with single -
            .replace(/^-+/, '')             // Trim - from start of text
            .replace(/-+$/, '');            // Trim - from end of text
    }

    function showLoading() {
        loading.style.display = 'block';
        error.style.display = 'none';
        noResults.style.display = 'none';
        entityGrid.style.display = 'none';
    }

    function hideLoading() {
        loading.style.display = 'none';
        entityGrid.style.display = 'grid';
    }

    function showError() {
        error.style.display = 'block';
        loading.style.display = 'none';
        noResults.style.display = 'none';
        entityGrid.style.display = 'none';
    }

    function showNoResults() {
        noResults.style.display = 'block';
        loading.style.display = 'none';
        error.style.display = 'none';
        entityGrid.style.display = 'none';
    }

    async function fetchEntities() {
        const query = searchInput.value.trim();
        const dataset = datasetFilter.value;

        showLoading();

        try {
            const response = await fetch(`/api/entities?q=${encodeURIComponent(query)}&dataset=${encodeURIComponent(dataset)}`);
            if (!response.ok) throw new Error('Network response was not ok');
            
            const data = await response.json();
            
            if (!data.entities || data.entities.length === 0) {
                showNoResults();
                return;
            }

            entityGrid.innerHTML = '';
            data.entities.forEach(entity => {
                const card = createEntityCard(entity);
                entityGrid.appendChild(card);
            });

            hideLoading();
        } catch (err) {
            console.error('Error fetching entities:', err);
            showError();
        }
    }

    // Initial load
    fetchEntities();

    // Search input handler with debounce
    searchInput.addEventListener('input', function() {
        clearTimeout(debounceTimer);
        debounceTimer = setTimeout(fetchEntities, 300);
    });

    // Dataset filter handler
    datasetFilter.addEventListener('change', fetchEntities);
});
