with source as (
    select * from {{ source('healthflow_raw', 'medications') }}
),

renamed as (
    select
        patient_id,
        encounter_id,
        medication_code,
        medication_description,
        start_date,
        stop_date,
        is_active,
        base_cost,
        payer_coverage,
        total_cost,
        out_of_pocket,
        processed_at
    from source
    where patient_id is not null
)

select * from renamed
