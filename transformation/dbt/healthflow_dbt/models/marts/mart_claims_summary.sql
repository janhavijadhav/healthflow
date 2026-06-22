with encounters as (
    select * from {{ ref('stg_encounters') }}
),

patients as (
    select * from {{ ref('stg_patients') }}
),

claims as (
    select
        e.encounter_id,
        e.patient_id,
        e.provider_id,
        e.payer_id,
        e.encounter_class,
        e.description         as encounter_description,
        e.encounter_date,
        e.encounter_year,
        e.encounter_month,
        e.duration_hours,
        e.total_claim_cost,
        e.payer_coverage,
        e.out_of_pocket,
        p.gender,
        p.race,
        p.ethnicity,
        p.state,
        p.age_years,
        case
            when e.total_claim_cost = 0 then 'zero_cost'
            when e.total_claim_cost < 500 then 'low'
            when e.total_claim_cost < 5000 then 'medium'
            else 'high'
        end as cost_tier,
        case
            when p.age_years < 18 then 'pediatric'
            when p.age_years < 65 then 'adult'
            else 'senior'
        end as age_group
    from encounters e
    left join patients p on e.patient_id = p.patient_id
)

select * from claims
