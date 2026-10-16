
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
