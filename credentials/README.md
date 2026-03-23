# credentials/

This directory holds GCP Service Account keys used by the local Spark cluster
to authenticate against GCS, Firestore, and other GCP APIs.

**Files in this directory are gitignored — never commit them.**

## Setup

### 1. Create a Service Account (one-time)

```bash
# Create SA
gcloud iam service-accounts create lawmind-spark \
    --display-name "Lawmind local Spark" \
    --project YOUR_PROJECT_ID

# Grant required roles
gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
    --member "serviceAccount:lawmind-spark@YOUR_PROJECT_ID.iam.gserviceaccount.com" \
    --role "roles/storage.objectAdmin"        # read/write GCS

gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
    --member "serviceAccount:lawmind-spark@YOUR_PROJECT_ID.iam.gserviceaccount.com" \
    --role "roles/datastore.user"             # Firestore read/write
```

### 2. Download the key

```bash
gcloud iam service-accounts keys create credentials/service-account.json \
    --iam-account lawmind-spark@YOUR_PROJECT_ID.iam.gserviceaccount.com
```

The file must be named **`service-account.json`** — that is the path configured
in `spark/spark-defaults.conf` and `docker-compose.yml`.

## GKE authentication (Workload Identity — for when Spark runs ON GKE)

When Spark executors run as GKE pods they use **Workload Identity** instead of a
key file. Pods inherit the GCP identity from their Kubernetes Service Account.
No key file is needed on GKE — see the comment in `spark/spark-defaults.conf`.

```bash
# Bind K8s SA to GCP SA (one-time setup on GKE)
gcloud iam service-accounts add-iam-policy-binding \
    lawmind-spark@YOUR_PROJECT_ID.iam.gserviceaccount.com \
    --role roles/iam.workloadIdentityUser \
    --member "serviceAccount:YOUR_PROJECT_ID.svc.id.goog[spark/spark]"

kubectl annotate serviceaccount spark \
    --namespace spark \
    iam.gke.io/gcp-service-account=lawmind-spark@YOUR_PROJECT_ID.iam.gserviceaccount.com
```
