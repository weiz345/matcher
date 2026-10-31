# Local visual similarity experiment

A separate synthetic gallery and CLIP nearest-neighbor experiment. No dating-account data or Supabase access. Uploaded queries remain in request memory and are not stored. This is a local development server without authentication; use it on a trusted network.

## Run

From `/home/zhengw/hinge-mini` (requires `uvx`, Python, internet for downloads):

```bash
uvx --with pillow python image_lab/download_dataset.py --sample sample4
uvx --with pillow python image_lab/download_dataset.py --sample sample --append
uvx --with numpy --with pillow --with onnxruntime python image_lab/build_index.py
uvx --with numpy --with pillow --with onnxruntime python image_lab/evaluate.py
./scripts/start_image_lab.sh --host 0.0.0.0 --port 8001
```

Open `http://localhost:8001` on the machine hosting this container, if port 8001 is forwarded; otherwise use the container's reachable IP and port. Current container URL: `http://10.244.21.93:8001`.

The two sample archives contain 700 + 750 synthetic images, yielding 1,450 images (all distinct file hashes). `--limit` limits extraction per archive; it cannot create more images than an archive contains. Rebuild the index and restart the lab after changing the gallery. Larger upstream archives exist but are multi-gigabyte downloads and are not fetched by this script.

## What to try

Choose **Browse gallery**, select a reference, set top-k, and search. Or upload a JPEG/PNG/WebP. Compare single-center-crop features against averaged original/mirror/inner-crop features, then change the query perturbation. Scores are cosine similarity, not probabilities. Gallery references exclude themselves by default; uploaded copies are not automatically deduplicated against the gallery.

The robustness tab shows three references tested with original, mirror, tighter crop and 12-degree image rotation. It measures the rank of the same underlying image, including itself in the candidates. These are easy sanity checks, not different camera angles or a measure of human resemblance.

## Limits and next experiment

CLIP measures broad visual similarity including hair, background, lighting, clothing, and expression. It is not a face identity encoder. Flip/crop averaging does not make it angle agnostic. Testing true pose robustness requires consented or synthetic multi-view subjects with known groups and held-out angles, then measuring recall@k across those views.

No ethnicity, gender, BMI or body-frame predictions or filters are implemented. The downloaded samples have no supplied labels for those properties. Use voluntarily supplied profile fields for demographic preferences; a portrait cannot reliably establish BMI or body frame. Body-shape matching would need a separate consented, full-body experiment and a clear definition of similarity. Do not interpret the rank as agreement on any of these properties.

The synthetic dataset includes varied apparent ages and is for isolated research, not an adult dating-profile seed corpus. No integration into the dating app is performed.

## Verification

With the server running and the index ready:

```bash
python3 image_lab/test_lab.py
uvx --with playwright python image_lab/test_browser.py
```

Browser test requires Chromium installed for Playwright. Evaluation checks self retrieval, result ordering and exclusion in addition to writing the visible report.

## Provenance

- [SFHQ synthetic dataset](https://github.com/SelfishGene/SFHQ-dataset), upstream MIT license saved in `data/SFHQ-LICENSE.txt`.
- [Download mirror](https://huggingface.co/datasets/bitmind/SyntheticFacesHQ), two sample ZIPs pinned by SHA-256 in the downloader.
- [CLIP ViT-B/32 quantized ONNX](https://huggingface.co/Xenova/clip-vit-base-patch32), approximately 89 MB, CPU ONNX Runtime inference. Model publisher/upstream model terms apply separately to the dataset license.
- 224-pixel center crops, normalized 512-dimensional embeddings, cosine nearest neighbors over all gallery rows. Model version and image IDs are validated when loading the index.

Downloads, model, index, evaluation previews and image files live in ignored `image_lab/data/`; source code and scripts are separate. Do not add real-user photos to the downloadable gallery.

Embedding progress appears above the query controls: processed/total images, percentage, elapsed time, images/second and estimated remaining time, refreshed every two seconds. Completed builds retain their duration. The builder writes progress atomically after each eight-image batch, including loading/saving/failure states, and prints periodic terminal progress. Remaining-time estimates use observed throughput and may vary with CPU load; download time is separate.
