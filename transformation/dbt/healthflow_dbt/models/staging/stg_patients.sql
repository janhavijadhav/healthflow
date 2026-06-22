with source as (
    select * from {{ source('healthflow_raw', 'patients') }}
),

renamed as (
    select
        patient_id,
        birth_date,
        death_date,
        gender,
        race,
        ethnicity,
        state,
        zip_code,
        age_years,
        is_deceased,
        processed_at
    from source
    where patient_id is not null
)

select * from renamed
