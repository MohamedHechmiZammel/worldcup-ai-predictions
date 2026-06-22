import argparse
import asyncio
import datetime
import joblib
from pathlib import Path

from sqlalchemy import update

from app.core.database import AsyncSessionLocal
from app.models.model_version import ModelVersion


async def register(artifact_path: str, version: str, model_type: str, description: str) -> None:
    # joblib.load deserializes a pickle-based artifact produced by our own
    # training pipeline (train_model.py) and stored in a controlled, internal
    # path.  The artifact is never accepted from untrusted/external sources, so
    # the pickle execution risk is acceptable here.
    artifact = joblib.load(artifact_path)

    async with AsyncSessionLocal() as session:
        async with session.begin():
            # deactivate existing active model of same type
            await session.execute(
                update(ModelVersion)
                .where(ModelVersion.model_type == model_type, ModelVersion.is_active == True)
                .values(is_active=False)
            )

            # insert new active version
            mv = ModelVersion(
                version=version,
                model_type=model_type,
                training_date=datetime.date.fromisoformat(artifact.get("training_date", str(datetime.date.today()))),
                description=description,
                artifact_path=str(Path(artifact_path).resolve()),
                accuracy_on_val=artifact.get("val_accuracy"),
                is_active=True,
            )
            session.add(mv)

    print(f"Registered model {version} ({model_type}) as active.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--artifact-path", required=True)
    parser.add_argument("--version", required=True)
    parser.add_argument("--model-type", required=True, choices=["prematch", "ingame"])
    parser.add_argument("--description", default="")
    args = parser.parse_args()
    asyncio.run(register(args.artifact_path, args.version, args.model_type, args.description))
