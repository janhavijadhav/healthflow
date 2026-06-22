with source as (
    select * from {{ source('healthflow_raw', 'conditions') }}
),

renamed as (
    select
        patient_id,
        encounter_id,
        condition_code,
        condition_description,
        onset_date,
        resolution_date,
        is_chronic,
        days_active,
        processed_at
    from source
    where patient_id is not null
)

select * from renamed
