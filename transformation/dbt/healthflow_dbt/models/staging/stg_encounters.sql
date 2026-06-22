with source as (
    select * from {{ source('healthflow_raw', 'encounters') }}
),

renamed as (
    select
        encounter_id,
        patient_id,
        provider_id,
        payer_id,
        encounter_class,
        encounter_code,
        description,
        encounter_start,
        encounter_stop,
        encounter_date,
        encounter_year,
        encounter_month,
        duration_hours,
        base_cost,
        total_claim_cost,
        payer_coverage,
        out_of_pocket,
        processed_at
    from source
    where encounter_id is not null
)

select * from renamed
