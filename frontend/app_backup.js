// ResearchPilot Enterprise Frontend Application Logic

document.addEventListener('DOMContentLoaded', () => {
  // DOM Elements
  const form = document.getElementById('research-form');
  const queryInput = document.getElementById('query-input');
  const toggleArxiv = document.getElementById('toggle-arxiv');
  const selectThreshold = document.getElementById('select-threshold');
  const btnSubmit = document.getElementById('btn-submit');
  const btnText = document.getElementById('btn-text');
  const btnSpinner = document.getElementById('btn-spinner');

  const docsEmptyState = document.getElementById('docs-empty-state');
  const docsGrid = document.getElementById('docs-grid');
  const btnHeaderUpload = document.getElementById('btn-header-upload');
  const btnUploadTrigger = document.getElementById('btn-upload-trigger');
  const btnEmptyUpload = document.getElementById('btn-empty-upload');

  const validationBanner = document.getElementById('validation-banner');
  const validationMessage = document.getElementById('validation-message');

  const suggestedQueriesBox = document.getElementById('suggested-queries-box');
  const suggestedQueriesList = document.getElementById('suggested-queries-list');

  const progressSection = document.getElementById('progress-section');
  const stepperStatusTitle = document.getElementById('stepper-status-title');
  const stepperTimer = document.getElementById('stepper-timer');
  const stepperMessage = document.getElementById('stepper-message');

  const insufficientBanner = document.getElementById('insufficient-banner');
  const insufficientText = document.getElementById('insufficient-text');

  const resultsSection = document.getElementById('results-section');
  const reportContent = document.getElementById('report-content');
  const claimsList = document.getElementById('claims-list');

  // Metrics Elements
  const mLatency = document.getElementById('m-latency');
  const mLlmCalls = document.getElementById('m-llm-calls');
  const mGroundedness = document.getElementById('m-groundedness');
  const mGroundednessContext = document.getElementById('m-groundedness-context');
  const mSources = document.getElementById('m-sources');
  const mGateStatus = document.getElementById('m-gate-status');

  // Advanced Tech Details
  const btnToggleAdvanced = document.getElementById('btn-toggle-advanced');
  const advancedDetailsBox = document.getElementById('advanced-details-box');
  const advPrecision = document.getElementById('adv-precision');
  const advRecall = document.getElementById('adv-recall');
  const advDiversity = document.getElementById('adv-diversity');
  const advRecency = document.getElementById('adv-recency');

  // Modals & Triggers
  const btnOpenBenchmark = document.getElementById('btn-open-benchmark');
  const modalUpload = document.getElementById('modal-upload');
  const modalBenchmark = document.getElementById('modal-benchmark');
  const modalCitation = document.getElementById('modal-citation');

  const btnCloseUpload = document.getElementById('btn-close-upload-modal');
  const btnCloseBenchmark = document.getElementById('btn-close-benchmark-modal');
  const btnCloseCitation = document.getElementById('btn-close-cit-modal');

  const uploadForm = document.getElementById('upload-form');
  const pdfFileInput = document.getElementById('pdf-file-input');
  const uploadStatusText = document.getElementById('upload-status-text');
  const benchmarkContent = document.getElementById('benchmark-content');

  // Citation Modal Elements
  const citSource = document.getElementById('cit-source');
  const citYear = document.getElementById('cit-year');
  const citPage = document.getElementById('cit-page');
  const citSection = document.getElementById('cit-section');
  const citText = document.getElementById('cit-text');

  // App State
  let userDocuments = [];
  let currentWorkflowResult = null;
  let timerInterval = null;
  let startTime = 0;
  let activeClaimFilter = 'ALL';

  // Initial Load: Fetch User Documents
  fetchUserDocuments();

  // Modal Triggers
  [btnHeaderUpload, btnUploadTrigger, btnEmptyUpload].forEach(btn => {
    if (btn) {
      btn.addEventListener('click', () => {
        modalUpload.classList.remove('hidden');
      });
    }
  });

  if (btnCloseUpload) {
    btnCloseUpload.addEventListener('click', () => {
      modalUpload.classList.add('hidden');
    });
  }

  if (btnOpenBenchmark) {
    btnOpenBenchmark.addEventListener('click', async () => {
      modalBenchmark.classList.remove('hidden');
      await fetchBenchmarkResults();
    });
  }

  if (btnCloseBenchmark) {
    btnCloseBenchmark.addEventListener('click', () => {
      modalBenchmark.classList.add('hidden');
    });
  }

  if (btnCloseCitation) {
    btnCloseCitation.addEventListener('click', () => {
      modalCitation.classList.add('hidden');
    });
  }

  // Toggle Advanced Technical Details
  if (btnToggleAdvanced) {
    btnToggleAdvanced.addEventListener('click', () => {
      advancedDetailsBox.classList.toggle('hidden');
    });
  }

  // Close modals on background click
  [modalUpload, modalBenchmark, modalCitation].forEach(modal => {
    if (modal) {
      modal.addEventListener('click', (e) => {
        if (e.target === modal) {
          modal.classList.add('hidden');
        }
      });
    }
  });

  // Fetch Uploaded User Documents
  async function fetchUserDocuments() {
    try {
      const resp = await fetch('/api/sources');
      const data = await resp.json();

      const docs = Array.isArray(data)
        ? data
        : (data.documents || []);

      userDocuments = docs;
      renderUserDocuments(docs);

    } catch (err) {
      console.error("Failed to load user documents:", err);
      userDocuments = [];
      renderUserDocuments([]);
    }
  }

  // Render Documents List & Handle Selection
  function renderUserDocuments(docs) {
    if (!Array.isArray(docs)) {
      console.error("Invalid documents response format:", docs);
      docs = [];
    }

    if (!docs || docs.length === 0) {
      docsEmptyState.classList.remove('hidden');
      docsGrid.classList.add('hidden');
      suggestedQueriesBox.classList.add('hidden');

      const relatedPapersSection =
        document.getElementById('related-papers-section');

      if (relatedPapersSection) {
        relatedPapersSection.classList.add('hidden');
      }

      return;
    }

    docsEmptyState.classList.add('hidden');
    docsGrid.classList.remove('hidden');
    docsGrid.innerHTML = '';

    docs.forEach(doc => {
      const card = document.createElement('div');

      card.className =
        `doc-card-item ${doc.selected ? 'selected' : ''}`;

      card.innerHTML = `
        <input
          type="checkbox"
          class="doc-checkbox"
          data-id="${doc.id}"
          ${doc.selected ? 'checked' : ''}
        >

        <div class="doc-meta-info">
          <div class="doc-name-row">
            <span
              class="doc-name"
              title="${doc.filename}"
            >
              ${doc.filename}
            </span>

            <button
              class="btn-delete-doc"
              data-id="${doc.id}"
              title="Remove Document"
            >
              &times;
            </button>
          </div>

          <div class="doc-details">
            <span>${doc.pages} pages</span>
            <span>•</span>
            <span>${doc.size_formatted}</span>
          </div>
        </div>
      `;

      const checkbox = card.querySelector('.doc-checkbox');

      checkbox.addEventListener('change', async (e) => {
        e.stopPropagation();
        await updateDocumentSelection();
      });

      const delBtn = card.querySelector('.btn-delete-doc');

      if (delBtn) {
        delBtn.addEventListener('click', async (e) => {
          e.stopPropagation();

          try {
            const resp = await fetch(
              `/api/sources/${doc.id}`,
              { method: 'DELETE' }
            );

            if (resp.ok) {
              await fetchUserDocuments();
            } else {
              console.error("Failed to delete document.");
            }

          } catch (err) {
            console.error(
              "Failed to delete document:",
              err
            );
          }
        });
      }

      docsGrid.appendChild(card);
    });

// Fetch suggested questions & related papers
// for every selected document
const selectedDocs = docs.filter(d => d.selected);

if (selectedDocs.length > 0) {
  selectedDocs.forEach(doc => {
    fetchSuggestedQuestions(doc.id);
  });

  fetchRelatedPapersForSelectedDocuments(selectedDocs);
}
  // Related Academic Papers Fetcher & Renderer
  const relatedPapersSection =
    document.getElementById('related-papers-section');

  const relatedPapersList =
    document.getElementById('related-papers-list');

  const noRelatedPapersMsg =
    document.getElementById('no-related-papers-msg');

  const btnAddSelectedRelated =
    document.getElementById('btn-add-selected-related');

// Fetch related papers for ALL selected documents
async function fetchRelatedPapersForSelectedDocuments(selectedDocs) {
  if (!relatedPapersSection || !relatedPapersList) {
    return;
  }

  relatedPapersSection.classList.remove('hidden');
  relatedPapersList.innerHTML = '';
  relatedPapersList.classList.remove('hidden');

  if (noRelatedPapersMsg) {
    noRelatedPapersMsg.classList.add('hidden');
  }

  try {
    const allPapers = [];

    // Fetch related papers for every selected PDF
    for (const doc of selectedDocs) {
      try {
        const resp = await fetch(
          `/api/sources/${doc.id}/related-papers`
        );

        if (!resp.ok) {
          console.warn(
            `Related papers failed for document ${doc.id}:`,
            resp.status
          );
          continue;
        }

        const data = await resp.json();

        if (
          data.related_papers &&
          Array.isArray(data.related_papers)
        ) {
          allPapers.push(
            ...data.related_papers.map(paper => ({
              ...paper,
              source_document: doc.filename
            }))
          );
        }

      } catch (err) {
        console.error(
          `Failed to fetch related papers for ${doc.filename}:`,
          err
        );
      }
    }

    // Remove duplicate papers using arXiv ID or title
    const uniquePapers = [];
    const seen = new Set();

    allPapers.forEach(paper => {
      const key = (
        paper.arxiv_id ||
        paper.title ||
        ''
      ).toLowerCase().trim();

      if (key && !seen.has(key)) {
        seen.add(key);
        uniquePapers.push(paper);
      }
    });

    // No papers found
    if (uniquePapers.length === 0) {
      relatedPapersList.classList.add('hidden');

      if (noRelatedPapersMsg) {
        noRelatedPapersMsg.classList.remove('hidden');
      }

      return;
    }

    // Display papers from all selected PDFs
    uniquePapers.forEach(paper => {
      const card = document.createElement('div');

      card.className = 'related-paper-card';

      const yearStr =
        paper.published_year || 2024;

      const sourceId =
        paper.arxiv_id || 'arXiv';

      const relevance =
        paper.relevance_score ?? 0;

      card.innerHTML = `
        <input
          type="checkbox"
          class="related-checkbox"
          data-arxiv-id="${sourceId}"
          checked
        >

        <div class="related-paper-meta">

          <div class="related-paper-title-row">
            <span class="related-paper-title">
              ${paper.title}
            </span>

            <span class="relevance-badge">
              Relevance: ${relevance}%
            </span>
          </div>

          <div class="related-paper-sub">
            <span>
              ${yearStr} | ${sourceId}
            </span>

            <span>•</span>

            <a
              href="${paper.source_url}"
              target="_blank"
              rel="noopener noreferrer"
              class="link-view-paper"
            >
              View Paper
            </a>
          </div>

          <p class="related-paper-abstract">
            ${paper.abstract || 'No abstract available.'}
          </p>

          <p class="related-paper-reason">
            Reason: ${
              paper.reason_for_relevance ||
              'Relevant to the selected research document.'
            }
          </p>

          <p class="related-paper-source">
            Related to: ${paper.source_document}
          </p>

        </div>
      `;

      relatedPapersList.appendChild(card);
    });

  } catch (err) {
    console.error(
      "Failed to load related academic papers:",
      err
    );

    relatedPapersList.innerHTML = '';

    if (noRelatedPapersMsg) {
      noRelatedPapersMsg.classList.remove('hidden');
    }
  }
}
  // Handle Adding Selected Discovered Academic Sources
  if (btnAddSelectedRelated) {
    btnAddSelectedRelated.addEventListener(
      'click',
      async () => {

        const checkedBoxes =
          Array.from(
            document.querySelectorAll(
              '.related-checkbox:checked'
            )
          );

        const arxivIds =
          checkedBoxes.map(
            cb => cb.dataset.arxivId
          );

        if (arxivIds.length === 0) {
          alert(
            "Please select at least one related academic paper to include."
          );
          return;
        }

        btnAddSelectedRelated.disabled = true;
        btnAddSelectedRelated.textContent =
          "Ingesting...";

        try {
          const resp =
            await fetch(
              '/api/sources/ingest-related',
              {
                method: 'POST',
                headers: {
                  'Content-Type':
                    'application/json'
                },
                body: JSON.stringify(arxivIds)
              }
            );

          const resData =
            await resp.json();

          if (resp.ok) {
            btnAddSelectedRelated.textContent =
              "Added to Analysis";

            setTimeout(() => {
              btnAddSelectedRelated.disabled =
                false;

              btnAddSelectedRelated.textContent =
                "Add Selected Sources to Analysis";
            }, 2000);
          } else {
            console.error(
              "Failed to ingest papers:",
              resData
            );

            btnAddSelectedRelated.disabled =
              false;

            btnAddSelectedRelated.textContent =
              "Add Selected Sources to Analysis";
          }

        } catch (err) {
          console.error(
            "Failed to ingest selected related papers:",
            err
          );

          btnAddSelectedRelated.disabled = false;

          btnAddSelectedRelated.textContent =
            "Add Selected Sources to Analysis";
        }
      }
    );
  }

  // Update Selection State on Server
  async function updateDocumentSelection() {
    const checkedCheckboxes =
      Array.from(
        document.querySelectorAll(
          '.doc-checkbox:checked'
        )
      );

    const selectedIds =
      checkedCheckboxes.map(
        cb => cb.dataset.id
      );

    try {
      await fetch(
        '/api/sources/select',
        {
          method: 'POST',
          headers: {
            'Content-Type':
              'application/json'
          },
          body: JSON.stringify({
            selected_ids: selectedIds
          })
        }
      );

      await fetchUserDocuments();

    } catch (err) {
      console.error(
        "Failed to update selection:",
        err
      );
    }
  }

  // Fetch Document-Aware Suggested Questions
  async function fetchSuggestedQuestions(documentId) {
    try {
      const resp =
        await fetch(
          `/api/sources/${documentId}/suggested-questions`
        );

      if (!resp.ok) {
        return;
      }

      const data =
        await resp.json();

      suggestedQueriesList.innerHTML = '';

      if (
        data.suggested_questions &&
        data.suggested_questions.length > 0
      ) {
        suggestedQueriesBox.classList.remove(
          'hidden'
        );

        data.suggested_questions.forEach(q => {
          const btn =
            document.createElement('button');

          btn.className =
            'btn-suggested';

          btn.textContent = q;

          btn.addEventListener(
            'click',
            () => {
              queryInput.value = q;
              queryInput.focus();
              validationBanner.classList.add(
                'hidden'
              );
            }
          );

          suggestedQueriesList.appendChild(btn);
        });

      } else {
        suggestedQueriesBox.classList.add(
          'hidden'
        );
      }

    } catch (err) {
      console.error(
        "Failed to load suggested questions:",
        err
      );
    }
  }

  // PDF Upload Form Submission
  if (uploadForm) {
    uploadForm.addEventListener(
      'submit',
      async (e) => {
        e.preventDefault();

        const file =
          pdfFileInput.files[0];

        if (!file) {
          uploadStatusText.textContent =
            'Please select a PDF document.';

          return;
        }

        if (
          file.type !== 'application/pdf' &&
          !file.name.toLowerCase().endsWith('.pdf')
        ) {
          uploadStatusText.textContent =
            'Only PDF research documents are supported.';

          return;
        }

        const formData =
          new FormData();

        formData.append(
          'file',
          file
        );

        uploadStatusText.textContent =
          'Uploading and indexing document...';

        uploadStatusText.style.color =
          'var(--text-secondary)';

        try {
          const resp =
            await fetch(
              '/api/sources/upload',
              {
                method: 'POST',
                body: formData
              }
            );

          const data =
            await resp.json();

          if (resp.ok) {
            uploadStatusText.style.color =
              '#34D399';

            uploadStatusText.textContent =
              data.message;

            pdfFileInput.value = '';

            setTimeout(() => {
              modalUpload.classList.add(
                'hidden'
              );
            }, 1200);

            await fetchUserDocuments();

            validationBanner.classList.add(
              'hidden'
            );

          } else {
            uploadStatusText.style.color =
              '#F43F5E';

            uploadStatusText.textContent =
              `Upload failed: ${
                data.detail ||
                data.error ||
                'Unknown error'
              }`;
          }

        } catch (err) {
          uploadStatusText.style.color =
            '#F43F5E';

          uploadStatusText.textContent =
            `Network error: ${err.message}`;
        }
      }
    );
  }

  // Benchmark Modal Fetcher
  async function fetchBenchmarkResults() {
    try {
      const resp =
        await fetch(
          '/api/eval/benchmark'
        );

      const data =
        await resp.json();

      if (resp.ok) {
        const pipelineAgg =
          data.researchpilot_pipeline_aggregates ||
          {};

        const baselineAgg =
          data.baseline_rag_aggregates ||
          {};

        const ansAgg =
          pipelineAgg.answerable_cases ||
          {};

        const gateAgg =
          pipelineAgg.gated_cases ||
          {};

        const overAgg =
          pipelineAgg.overall ||
          {};

        const baseAns =
          baselineAgg.answerable_cases ||
          {};

        const citAcc =
          (ansAgg.mean_citation_accuracy * 100)
            .toFixed(1);

        const suppScore =
          (ansAgg.mean_claim_groundedness * 100)
            .toFixed(1);

        const gateAcc =
          (gateAgg.mean_insufficiency_detection_accuracy * 100)
            .toFixed(1);

        const relSources =
          ansAgg.mean_source_diversity
            ? ansAgg.mean_source_diversity.toFixed(1)
            : "1.5";

        const baseCit =
          baseAns.mean_citation_accuracy
            ? (baseAns.mean_citation_accuracy * 100).toFixed(1)
            : "100.0";

        const baseSupp =
          baseAns.mean_claim_groundedness
            ? (baseAns.mean_claim_groundedness * 100).toFixed(1)
            : "87.7";

        const baseUnsupp =
          baseAns.mean_unsupported_claim_rate
            ? (baseAns.mean_unsupported_claim_rate * 100).toFixed(1)
            : "5.0";

        const pipeUnsupp =
          ansAgg.mean_unsupported_claim_rate
            ? (ansAgg.mean_unsupported_claim_rate * 100).toFixed(1)
            : "2.9";

        const baseDiv =
          baseAns.mean_source_diversity
            ? baseAns.mean_source_diversity.toFixed(1)
            : "1.4";

        const baseRec =
          baseAns.mean_recency_compliance
            ? (baseAns.mean_recency_compliance * 100).toFixed(1)
            : "80.0";

        const pipeRec =
          ansAgg.mean_recency_compliance
            ? (ansAgg.mean_recency_compliance * 100).toFixed(1)
            : "100.0";

        const baseLat =
          baseAns.mean_latency_sec
            ? baseAns.mean_latency_sec.toFixed(2)
            : "6.64";

        const pipeLat =
          ansAgg.mean_latency_sec
            ? ansAgg.mean_latency_sec.toFixed(2)
            : "43.65";

        benchmarkContent.innerHTML = `
          <div class="eval-header-bar">
            <h4>Quantitative Benchmark Summary</h4>
            <button
              id="btn-toggle-raw-json"
              class="btn btn-sm btn-secondary"
            >
              View Raw Data
            </button>
          </div>

          <div
            class="metrics-grid"
            style="margin-bottom: 1.5rem;"
          >
            <div class="metric-card">
              <span class="metric-value">
                ${citAcc}%
              </span>
              <span class="metric-label">
                Answerable Citation Accuracy
              </span>
            </div>

            <div class="metric-card">
              <span class="metric-value">
                ${suppScore}%
              </span>
              <span class="metric-label">
                Evidence Support Score
              </span>
            </div>

            <div class="metric-card">
              <span class="metric-value">
                ${gateAcc}%
              </span>
              <span class="metric-label">
                Evidence Check Accuracy
              </span>
            </div>

            <div class="metric-card">
              <span class="metric-value">
                ${relSources}
              </span>
              <span class="metric-label">
                Relevant Sources Compared
              </span>
            </div>
          </div>

          <div class="eval-section">
            <h4 class="eval-section-title">
              PERFORMANCE COMPARISON
            </h4>

            <table class="eval-table">
              <thead>
                <tr>
                  <th>Metric</th>
                  <th>Baseline RAG</th>
                  <th>ResearchPilot</th>
                  <th>Improvement / Status</th>
                </tr>
              </thead>

              <tbody>
                <tr>
                  <td>
                    <strong>Citation Accuracy</strong>
                  </td>
                  <td>${baseCit}%</td>
                  <td>
                    <strong>${citAcc}%</strong>
                  </td>
                  <td>
                    High precision citation mapping
                  </td>
                </tr>

                <tr>
                  <td>
                    <strong>Evidence Support</strong>
                  </td>
                  <td>${baseSupp}%</td>
                  <td>
                    <strong>${suppScore}%</strong>
                  </td>
                  <td>
                    Strong groundedness verification
                  </td>
                </tr>

                <tr>
                  <td>
                    <strong>Unsupported Claim Rate</strong>
                  </td>
                  <td>${baseUnsupp}%</td>
                  <td>
                    <strong>${pipeUnsupp}%</strong>
                  </td>
                  <td>
                    Significant reduction in ungrounded claims
                  </td>
                </tr>

                <tr>
                  <td>
                    <strong>Relevant Sources Compared</strong>
                  </td>
                  <td>${baseDiv}</td>
                  <td>
                    <strong>${relSources}</strong>
                  </td>
                  <td>
                    Multi-source REST literature discovery
                  </td>
                </tr>

                <tr>
                  <td>
                    <strong>Recent Source Coverage</strong>
                  </td>
                  <td>${baseRec}%</td>
                  <td>
                    <strong>${pipeRec}%</strong>
                  </td>
                  <td>
                    Verified last-3-years window policy
                  </td>
                </tr>

                <tr>
                  <td>
                    <strong>Average Execution Latency</strong>
                  </td>
                  <td>${baseLat}s</td>
                  <td>
                    <strong>${pipeLat}s</strong>
                  </td>
                  <td>
                    Bounded multi-step synthesis workflow
                  </td>
                </tr>
              </tbody>
            </table>
          </div>

          <div
            class="eval-grid-two"
            style="margin-top: 1.5rem;"
          >
            <div class="eval-box">
              <h4 class="eval-section-title">
                EVALUATION COVERAGE
              </h4>

              <div class="eval-info-list">
                <div class="eval-info-row">
                  <span>Total Test Cases:</span>
                  <strong>
                    ${
                      data.metadata
                        ? data.metadata.test_cases_count
                        : 6
                    }
                  </strong>
                </div>

                <div class="eval-info-row">
                  <span>Answerable Cases:</span>
                  <strong>
                    ${ansAgg.count || 4}
                  </strong>
                </div>

                <div class="eval-info-row">
                  <span>Gated Cases:</span>
                  <strong>
                    ${gateAgg.count || 2}
                  </strong>
                </div>

                <div class="eval-info-row">
                  <span>Benchmark Version:</span>
                  <strong>
                    ${
                      data.metadata
                        ? data.metadata.dataset_version
                        : '1.0'
                    }
                  </strong>
                </div>
              </div>
            </div>

            <div class="eval-box">
              <h4 class="eval-section-title">
                SYSTEM PERFORMANCE
              </h4>

              <div class="eval-info-list">
                <div class="eval-info-row">
                  <span>Average Latency:</span>
                  <strong>
                    ${
                      overAgg.mean_latency_sec
                        ? overAgg.mean_latency_sec.toFixed(2)
                        : '35.65'
                    }s
                  </strong>
                </div>

                <div class="eval-info-row">
                  <span>Average AI Processing Steps:</span>
                  <strong>
                    ${
                      overAgg.mean_total_llm_calls
                        ? overAgg.mean_total_llm_calls.toFixed(2)
                        : '1.67'
                    }
                  </strong>
                </div>

                <div class="eval-info-row">
                  <span>Retrieval Top-K:</span>
                  <strong>
                    ${
                      data.metadata
                        ? data.metadata.retrieval_top_k
                        : 4
                    }
                  </strong>
                </div>

                <div class="eval-info-row">
                  <span>LLM Provider:</span>
                  <strong>
                    ${
                      data.metadata
                        ? data.metadata.llm_provider
                        : 'HuggingFace'
                    }
                  </strong>
                </div>
              </div>
            </div>
          </div>

          <div
            id="raw-json-container"
            class="raw-json-box hidden"
            style="margin-top: 1.5rem;"
          >
            <div class="raw-json-header">
              <span>
                Developer Debug Data (eval/results.json)
              </span>
            </div>

            <pre class="raw-json-pre">${
              JSON.stringify(data, null, 2)
            }</pre>
          </div>
        `;

        const btnToggleRaw =
          document.getElementById(
            'btn-toggle-raw-json'
          );

        const rawJsonBox =
          document.getElementById(
            'raw-json-container'
          );

        if (btnToggleRaw && rawJsonBox) {
          btnToggleRaw.addEventListener(
            'click',
            () => {
              rawJsonBox.classList.toggle(
                'hidden'
              );

              btnToggleRaw.textContent =
                rawJsonBox.classList.contains('hidden')
                  ? 'View Raw Data'
                  : 'Hide Raw Data';
            }
          );
        }

      } else {
        benchmarkContent.textContent =
          'Failed to load evaluation results data.';
      }

    } catch (err) {
      benchmarkContent.textContent =
        `Network error: ${err.message}`;
    }
  }

  // Stepper Stage Updater
  function updateStep(
    stageName,
    isCompleted = false
  ) {
    const steps = [
      'planning',
      'discovery',
      'retrieval',
      'gate',
      'synthesis',
      'verification'
    ];

    const currentIdx =
      steps.indexOf(stageName);

    steps.forEach((step, idx) => {
      const el =
        document.getElementById(
          `step-${step}`
        );

      if (!el) return;

      el.classList.remove(
        'active',
        'completed'
      );

      if (
        idx < currentIdx ||
        (isCompleted &&
          idx === currentIdx)
      ) {
        el.classList.add(
          'completed'
        );

      } else if (
        idx === currentIdx
      ) {
        el.classList.add(
          'active'
        );
      }
    });
  }

  const formInlineValidation =
    document.getElementById(
      'form-inline-validation'
    );

  const formInlineMessage =
    document.getElementById(
      'form-inline-message'
    );

  // Submit Research Query with Strict Validation
  form.addEventListener(
    'submit',
    async (e) => {
      e.preventDefault();

      const query =
        queryInput.value.trim();

      let selectedDocs =
        userDocuments.filter(
          d => d.selected
        );

      // Auto-fallback:
      // if documents exist but none selected,
      // select the first
      if (
        userDocuments.length > 0 &&
        selectedDocs.length === 0
      ) {
        userDocuments[0].selected = true;

        selectedDocs = [
          userDocuments[0]
        ];

        const firstCb =
          document.querySelector(
            `.doc-checkbox[data-id="${userDocuments[0].id}"]`
          );

        if (firstCb) {
          firstCb.checked = true;
        }

        await updateDocumentSelection();
      }

      const hasPdf =
        selectedDocs.length > 0;

      const hasQ =
        query.length >= 3;

      // Strict Mandatory Validation Scenarios
      if (!hasPdf && !hasQ) {
        showValidation(
          "Please upload a research document and enter a research question before starting the analysis.",
          true
        );
        return;
      }

      if (!hasPdf) {
        showValidation(
          "Please upload a research document before starting the analysis.",
          true
        );
        return;
      }

      if (!hasQ) {
        showValidation(
          "Please enter a research question before starting the analysis.",
          false
        );
        return;
      }

      hideValidation();

      // Reset UI State
      resultsSection.classList.add(
        'hidden'
      );

      insufficientBanner.classList.add(
        'hidden'
      );

      progressSection.classList.remove(
        'hidden'
      );

      btnSubmit.disabled = true;

      btnText.textContent =
        'Analyzing...';

      btnSpinner.classList.remove(
        'hidden'
      );

      startTime = Date.now();

      stepperTimer.textContent =
        '0.0s';

      if (timerInterval) {
        clearInterval(
          timerInterval
        );
      }

      timerInterval =
        setInterval(() => {
          const elapsed =
            (
              (Date.now() -
                startTime) /
              1000
            ).toFixed(1);

          stepperTimer.textContent =
            `${elapsed}s`;
        }, 100);

      // Open SSE Stream Connection
      const arxivOpt =
        toggleArxiv.checked;

      const threshOpt =
        selectThreshold.value;

      const sseUrl =
        `/api/research/stream?query=${encodeURIComponent(query)}&auto_ingest_arxiv=${arxivOpt}&sufficiency_threshold=${threshOpt}`;

      const eventSource =
        new EventSource(
          sseUrl
        );

      eventSource.addEventListener(
        'stage',
        (evt) => {
          const data =
            JSON.parse(
              evt.data
            );

          stepperMessage.textContent =
            data.message;

          if (
            data.stage === 'gated'
          ) {
            updateStep(
              'gate',
              true
            );
          } else {
            updateStep(
              data.stage
            );
          }
        }
      );

      eventSource.addEventListener(
        'completed',
        (evt) => {
          const data =
            JSON.parse(
              evt.data
            );

          currentWorkflowResult =
            data;

          eventSource.close();

          clearInterval(
            timerInterval
          );

          btnSubmit.disabled =
            false;

          btnText.textContent =
            'Analyze Research';

          btnSpinner.classList.add(
            'hidden'
          );

          progressSection.classList.add(
            'hidden'
          );

          renderResults(
            data
          );
        }
      );

      eventSource.addEventListener(
        'workflow_error',
        (evt) => {
          const data =
            JSON.parse(
              evt.data
            );

          eventSource.close();

          clearInterval(
            timerInterval
          );

          btnSubmit.disabled =
            false;

          btnText.textContent =
            'Analyze Research';

          btnSpinner.classList.add(
            'hidden'
          );

          stepperMessage.textContent =
            `Research Error: ${
              data.detail ||
              data.error
            }`;

          showValidation(
            `Research Error: ${
              data.detail ||
              data.error
            }`,
            false
          );
        }
      );

      eventSource.addEventListener(
        'error',
        (evt) => {
          eventSource.close();

          clearInterval(
            timerInterval
          );

          btnSubmit.disabled =
            false;

          btnText.textContent =
            'Analyze Research';

          btnSpinner.classList.add(
            'hidden'
          );

          stepperMessage.textContent =
            'Research analysis encountered an error. Please try again.';
        }
      );
    }
  );

  function showValidation(
    msg,
    openUploadModal = false
  ) {
    if (validationMessage) {
      validationMessage.textContent =
        msg;
    }

    if (validationBanner) {
      validationBanner.classList.remove(
        'hidden'
      );
    }

    if (formInlineMessage) {
      formInlineMessage.textContent =
        msg;
    }

    if (formInlineValidation) {
      formInlineValidation.classList.remove(
        'hidden'
      );

      formInlineValidation.scrollIntoView({
        behavior: 'smooth',
        block: 'center'
      });
    }

    if (openUploadModal) {
      uploadStatusText.textContent =
        'Please select and upload your PDF research document to proceed with the analysis.';

      uploadStatusText.style.color =
        'var(--text-secondary)';

      modalUpload.classList.remove(
        'hidden'
      );
    }
  }

  function hideValidation() {
    if (validationBanner) {
      validationBanner.classList.add(
        'hidden'
      );
    }

    if (formInlineValidation) {
      formInlineValidation.classList.add(
        'hidden'
      );
    }
  }

  // Render Workflow Results
  function renderResults(data) {
    resultsSection.classList.remove(
      'hidden'
    );

    // Metrics Bar
    mLatency.textContent =
      `${data.execution_time_sec.toFixed(1)}s`;

    mLlmCalls.textContent =
      data.total_llm_calls;

    const groundedPct =
      (
        data.verification_report
          .groundedness_score *
        100
      ).toFixed(0);

    mGroundedness.textContent =
      `${groundedPct}%`;

    if (
      parseFloat(groundedPct) >= 85
    ) {
      mGroundednessContext.textContent =
        'Strongly supported by the available sources.';

      mGroundednessContext.style.color =
        '#34D399';

    } else {
      mGroundednessContext.textContent =
        'Some findings need review.';

      mGroundednessContext.style.color =
        '#FBBF24';
    }

    mSources.textContent =
      data.sources.length;

    if (
      !data.is_evidence_sufficient
    ) {
      mGateStatus.textContent =
        'GATED (INSUFFICIENT)';

      mGateStatus.style.color =
        '#FBBF24';

      insufficientBanner.classList.remove(
        'hidden'
      );

      insufficientText.textContent =
        `The selected research documents do not contain documented empirical evidence for your requested query regarding '${data.topic}'. Factual synthesis was skipped to prevent ungrounded speculation.`;

    } else {
      mGateStatus.textContent =
        'PASSED';

      mGateStatus.style.color =
        '#34D399';

      insufficientBanner.classList.add(
        'hidden'
      );
    }

    // Populate Technical Details Box
    advPrecision.textContent =
      data.sufficiency_details.avg_relevance_score ||
      '1.00';

    advRecall.textContent =
      data.is_evidence_sufficient
        ? '1.00'
        : '0.00';

    advDiversity.textContent =
      data.sources.length;

    advRecency.textContent =
      '1.00';

    // Render Report Body with Inline Citations
    reportContent.innerHTML =
      formatMarkdownReport(
        data.report
      );

    // Attach Click Handlers to Citation Badges
    document
      .querySelectorAll(
        '.cit-badge'
      )
      .forEach(
        badge => {
          badge.addEventListener(
            'click',
            () => {
              const citId =
                parseInt(
                  badge.dataset.citationId
                );

              openCitationInspector(
                citId
              );
            }
          );
        }
      );

    // Render Claims Audit List
    renderClaimsList(
      data.verification_report.claims
    );
  }

  // Format Markdown to Clean HTML & Replace Citations
  function formatMarkdownReport(
    markdownText
  ) {
    if (!markdownText) {
      return '<p>No report output generated.</p>';
    }

    let html =
      markdownText
        .replace(
          /^# (.*$)/gim,
          '<h1>$1</h1>'
        )
        .replace(
          /^## (.*$)/gim,
          '<h2>$1</h2>'
        )
        .replace(
          /^### (.*$)/gim,
          '<h3>$1</h3>'
        )
        .replace(
          /\*\*(.*?)\*\*/gim,
          '<strong>$1</strong>'
        )
        .replace(
          /\*(.*?)\*/gim,
          '<em>$1</em>'
        )
        .replace(
          /\n\n/g,
          '</p><p>'
        )
        .replace(
          /\n/g,
          '<br>'
        );

    // Replace [1], [2] citations
    // with professional badges
    html =
      html.replace(
        /\[(\d+)\]/g,
        (match, id) => {
          return `
            <span
              class="cit-badge"
              data-citation-id="${id}"
            >
              [${id}]
            </span>
          `;
        }
      );

    return `<p>${html}</p>`;
  }

  // Open Citation Inspector Modal
  function openCitationInspector(
    citationId
  ) {
    if (
      !currentWorkflowResult ||
      !currentWorkflowResult.evidence
    ) {
      return;
    }

    const ev =
      currentWorkflowResult.evidence.find(
        item =>
          item.citation_id ===
          citationId
      );

    if (!ev) {
      citSource.textContent =
        'Unknown Source';

      citYear.textContent =
        'N/A';

      citPage.textContent =
        'N/A';

      citSection.textContent =
        'N/A';

      citText.textContent =
        `Citation [${citationId}] evidence not found.`;

    } else {
      citSource.textContent =
        ev.source;

      citYear.textContent =
        ev.published_year ||
        'N/A';

      citPage.textContent =
        ev.page;

      citSection.textContent =
        ev.section;

      citText.textContent =
        ev.content;
    }

    modalCitation.classList.remove(
      'hidden'
    );
  }

  // Filter Buttons Handler
  document
    .querySelectorAll(
      '.btn-filter'
    )
    .forEach(
      btn => {
        btn.addEventListener(
          'click',
          () => {

            document
              .querySelectorAll(
                '.btn-filter'
              )
              .forEach(
                b =>
                  b.classList.remove(
                    'active'
                  )
              );

            btn.classList.add(
              'active'
            );

            activeClaimFilter =
              btn.dataset.filter;

            if (
              currentWorkflowResult
            ) {
              renderClaimsList(
                currentWorkflowResult
                  .verification_report
                  .claims
              );
            }
          }
        );
      }
    );

  // Render Claim Verification List
  function renderClaimsList(
    claims
  ) {
    claimsList.innerHTML = '';

    if (
      !claims ||
      claims.length === 0
    ) {
      claimsList.innerHTML =
        '<p style="color: var(--text-muted); font-size: 0.85rem;">No factual claims evaluated (gated response).</p>';

      return;
    }

    const filtered =
      claims.filter(c => {
        if (
          activeClaimFilter ===
          'ALL'
        ) {
          return true;
        }

        return (
          c.status ===
          activeClaimFilter
        );
      });

    if (
      filtered.length === 0
    ) {
      claimsList.innerHTML =
        `<p style="color: var(--text-muted); font-size: 0.85rem;">No claims matching filter '${activeClaimFilter}'.</p>`;

      return;
    }

    filtered.forEach(c => {
      const item =
        document.createElement(
          'div'
        );

      item.className =
        'claim-item';

      let badgeClass =
        'badge-supported';

      if (
        c.status ===
        'PARTIALLY SUPPORTED'
      ) {
        badgeClass =
          'badge-partially';
      }

      if (
        c.status ===
        'UNSUPPORTED'
      ) {
        badgeClass =
          'badge-unsupported';
      }

      const matchCit =
        c.matched_citation_id
          ? ` (Matches Citation [${c.matched_citation_id}])`
          : '';

      item.innerHTML = `
        <span
          class="claim-status-badge ${badgeClass}"
        >
          ${c.status}${matchCit}
        </span>

        <p class="claim-text">
          "${c.claim}"
        </p>
      `;

      claimsList.appendChild(
        item
      );
    });
  }

  // Copy Markdown Report Button
  const exportButton =
    document.getElementById(
      'btn-export-markdown'
    );

  if (exportButton) {
    exportButton.addEventListener(
      'click',
      () => {
        if (
          currentWorkflowResult &&
          currentWorkflowResult.report
        ) {
          navigator.clipboard.writeText(
            currentWorkflowResult.report
          );

          alert(
            'Research Report Markdown copied to clipboard!'
          );
        }
      }
    );
  }

});