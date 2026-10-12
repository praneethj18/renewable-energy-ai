from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.services.weather import get_weather, WeatherServiceError
from app.services.weather_storage import save_weather_data

router = APIRouter(prefix="/weather", tags=["Weather"])

# Default location: Hyderabad, Telangana, India
DEFAULT_LATITUDE = 17.385
DEFAULT_LONGITUDE = 78.487


@router.get("/")
def get_weather_forecast(
    latitude: float = Query(
        DEFAULT_LATITUDE,
        ge=-90,
        le=90,
        description="Latitude of the renewable energy site",
    ),
    longitude: float = Query(
        DEFAULT_LONGITUDE,
        ge=-180,
        le=180,
        description="Longitude of the renewable energy site",
    ),
    db: Session = Depends(get_db),
):
    try:
        weather_data = get_weather(
            latitude=latitude,
            longitude=longitude,
        )

        # Verify the provider returned the requested location.
        returned_location = weather_data.get("location", {})

        returned_latitude = returned_location.get("latitude")
        returned_longitude = returned_location.get("longitude")

        if (
            returned_latitude is None
            or returned_longitude is None
            or abs(returned_latitude - latitude) > 0.1
            or abs(returned_longitude - longitude) > 0.1
        ):
            raise HTTPException(
                status_code=502,
                detail="Weather provider returned an unexpected location.",
            )

        saved_count = save_weather_data(db, weather_data)

        return {
            "message": "Weather data retrieved and saved successfully",
            "saved_records": saved_count,
            "weather": weather_data,
        }

    except HTTPException:
        raise

    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail=str(exc),
        ) from exc

    except WeatherServiceError as exc:
        raise HTTPException(
            status_code=502,
            detail=str(exc),
        ) from exc

    except Exception as exc:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve or save weather data.",
        ) from exc