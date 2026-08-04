------------------------------------------------------------------------
-- Substrate.Invented.ELProjection  [RECONSTRUCTED from this session's own
-- tool calls. NOTE: the current substrate HEAD adds a ⟡ban-decompose gate
-- (no using/renaming/hiding/as on Substrate imports) — this file's `using`
-- imports would be REJECTED by that gate and must be rewritten to BARE
-- imports before committing. It typechecked (EXIT 0) at the HEAD it was
-- written against, on the CLEAN F2 vocabulary (bilinear-form-of was routed
-- around because F2/Vector/Universal.agda fails --safe on 2.6.3 =
-- ⊕SUBSTRATE-DEFECT). Verify against current HEAD.]
------------------------------------------------------------------------
{-# OPTIONS --safe --without-K #-}

module Substrate.Invented.ELProjection where

open import Substrate.Foundation.Nat using (ℕ)
open import Substrate.Foundation.Vec using (Vec; []; _∷_; zipWith; foldr)
open import Substrate.Algebra.F2 using (F₂; 𝟘; 𝟙; _+_; _·_)
open import Substrate.Algebra.F2.Vector using (Vector; _*ₛ_)

Sign : Set
Sign = F₂

present absent : Sign
present = 𝟙   -- ink / segment-sensitive
absent  = 𝟘   -- void / segment-antisensitive ("pure not-here")

Field : ℕ → Set
Field n = Vector n     -- a glyph field AND a segment field are this ONE type

-- MATCH = self-pairing = the F₂ dot product Σᵢ (glyphᵢ · segᵢ) = bilinear-form-of
-- metric-id, built directly from clean vocabulary ((·)=AND, sum=XOR-fold).
match : ∀ {n} → Field n → Field n → Sign
match v w = foldr (λ _ → F₂) _+_ 𝟘 (zipWith _·_ v w)

-- DEREZ as coverage-monotone scalar action (𝟘·s -> absent; never invents presence).
mask-off : ∀ {n} → Field n → Field n
mask-off v = 𝟘 *ₛ v

keep : ∀ {n} → Field n → Field n
keep v = 𝟙 *ₛ v
