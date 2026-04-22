<template>
  <section class="layout">
    <article class="card">
      <p class="card__label">Guest Access</p>
      <h2>Personal guest link</h2>
      <p>
        In MVP each invited family member opens the plan through a personal link without
        registration.
      </p>
    </article>

    <article class="card">
      <p class="card__label">Guest Rules</p>
      <ul>
        <li>Guests can read the full plan.</li>
        <li>Guests can add comments.</li>
        <li>Guests cannot create or edit plan items.</li>
        <li>All comments are visible to all participants.</li>
      </ul>
    </article>
  </section>
</template>

<style scoped>
.layout {
  display: grid;
  gap: 20px;
}

.card {
  padding: 24px;
  border: 1px solid rgba(39, 74, 103, 0.12);
  border-radius: 24px;
  background: rgba(255, 255, 255, 0.9);
}

.card__label {
  margin: 0 0 8px;
  color: #2c6f9e;
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.12em;
  text-transform: uppercase;
}

ul {
  margin: 0;
  padding-left: 20px;
}
</style>
