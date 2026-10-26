
function calculateDiscount(price, discount) {
  if (discount > 100) {
    return price;
  }

  return price - (price * discount) / 100;
}

function getUser(users, id) {
  return users.find((user) => user.id === id).name;
}

module.exports = {
  calculateDiscount,
  getUser,
};

// Testing CodePilot AI automatic pull request review
// Second automatic review test - PostgreSQL connected
// CodePilot AI production webhook test
